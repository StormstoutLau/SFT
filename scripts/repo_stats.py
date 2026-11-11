#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""repo_stats 视图层机械枚举校验器（stats 机读块 + 模式扫描 + 清单比对）——R7 视图层外推。

权威源：spec/repo-stats/REPO_STATS_DESIGN.md §4（stats 契约与校验规则集）
       + CODE_WIKI §10 ```stats 机读块（模式库/载体分类/声明/口径/基准的数据唯一登记处，I-4）。
与 m7_stats 的本质差异：对账器非重生成器——无 --write、无任何写通道（I-1），
prose 位点永不代改，只报偏差（DESIGN 方案 D 否决：prose 不可机械重建）。

不变式（DESIGN §8）：I-1 全模式只读 / I-2 确定性 / I-3 零新规则 / I-4 单一真值源
（模式库 = stats 块数据，代码零模式常量）/ I-5 异构于生成端 / I-6 声明=重数（两级：
declared vs 真值 P1；prose 命中值 vs 真值 P2/P3）/ I-7 修正轮产出自身在扫描范围（⑳轮新证）。

退出码：0 全部通过（含仅 P3）/ 1 发现 P1/P2 / 2 工具自身错误。

用法：
  python scripts/repo_stats.py              # verify 全量对账（本地直跑）
  python scripts/repo_stats.py --selftest   # 内嵌自测（20 fixture + F7 双变体 + I-1 只读断言，不触工作树）
  pre-commit：传入 staged 文件名，与对账作用域无交集即 skip
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
import shutil
from dataclasses import dataclass, field

# --- 仓库根（脚本位于 <root>/scripts/，与 cwd 无关，I-2） ---
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CODE_WIKI_PATH = "CODE_WIKI.md"
M7_PATH = "docs/M7_EVIDENCE_LOG.md"
DIS_PATH = "docs/discoveries/README.md"
PROGRESS_PATH = "docs/PROGRESS.md"
HOOKS_PATH = ".pre-commit-config.yaml"
SPEC_DIR = "spec"                    # templates 排除规则固定于枚举器语义（DESIGN §4.2）

# --- 对账作用域（hook 契约镜像：视图载体集 ∪ 真值源集，DESIGN §3.4） ---
SCOPE_RE = re.compile(
    r"^(CODE_WIKI\.md|README(\.en)?\.md|\.pre-commit-config\.yaml|docs/|spec/|adr/|scripts/)")

# --- 围栏与结构正则（I-4：结构性契约，非 prose 模式） ---
RE_STATS_FENCE = re.compile(r"```stats\n(.*?)\n```", re.S)          # CODE_WIKI 内恰一个
RE_HITS_FENCE = re.compile(r"```hits\n(.*?)\n```", re.S)            # M7 内直读
MACHINE_FENCE_OPEN = re.compile(r"^```(?:stats|rules|assertions|hits)\s*$")
RE_FM_VERSION = re.compile(r"^version:\s*(\S+)\s*$", re.M)
RE_DIS_ID = re.compile(r"DIS-(\d{3})")
RE_P_TASK = re.compile(r"^\|\s*P-\d{3}\s*\|")
RE_HOOK_ID = re.compile(r"^\s*-\s*id:")
RE_S2_HEADER = re.compile(r"^##\s*2[\.、]", re.M)
RE_S9_HEADER = re.compile(r"^##\s*9[\.、]", re.M)
RE_BUCKET_ROW = re.compile(r"^\|")
RE_VIEW_CARRIER = re.compile(r"CODE_WIKI|README|evidence\.svg")      # v1.1 口径载体判定
RE_S9_SPEC_LINK = re.compile(r"\(\./spec/([^/\s]+)/\)")
RE_VERSION_TOKEN = re.compile(r"v(\d+(?:\.\d+)+)")
RE_TREE_SPEC = re.compile(r"^[├└]──\s+spec/\s*$")
RE_TREE_ENTRY = re.compile(r"^    [├└]──\s+(\S+)")
RE_INT = re.compile(r"^\d+$")

# --- truth 绑定集（封闭枚举，DESIGN §4.2；扩展走 stats 块 + pattern_lib_version） ---
TRUTH_KEYS = (
    "fs.spec_feature_dirs", "fs.adr_files", "fs.dev_logs", "fs.scripts",
    "fs.templates", "fs.hooks", "fs.progress_tasks",
    "hits.samples", "hits.form2_total",
    "dis.range_min", "dis.range_max",
    "derived.view_layer_total", "derived.view_layer_pct",
)
DECLARED_KEYS = ("spec_feature_dirs", "adr_files", "dev_logs", "scripts",
                 "templates", "hooks", "progress_tasks")
FS_KEYS = tuple(k.split(".", 1)[1] for k in TRUTH_KEYS if k.startswith("fs."))


@dataclass(frozen=True)
class CheckResult:
    check_id: str      # "rs-stats" | "rs-truth" | "rs-decl" | "rs-pattern" | "rs-list"
    file: str
    severity: str      # "P1" | "P2" | "P3" | ""（空 = skip）
    message: str
    line: int | None = None
    gap: str | None = None   # drift-gate（pattern_lib_version ≥2）：意图→证据→缺口 三元组


class Summary:
    """违规 = P1/P2（阻断）；P3 = 门面快照滞后/基准漂移的信息性提示，非阻断（DESIGN §4.4）。"""

    def __init__(self, results):
        self.results = list(results)

    @property
    def violations(self):
        return [r for r in self.results if r.severity in ("P1", "P2")]

    @property
    def p3s(self):
        return [r for r in self.results if r.severity == "P3"]

    @property
    def passed(self):
        return not self.violations


@dataclass(frozen=True)
class PatternSpec:
    pid: str
    regex: re.Pattern
    truth: str                 # 单键或 "key1|key2" 双键
    scope: tuple[str, ...]     # 载体相对路径；空 = 全载体
    group: int                 # 对账捕获组索引（缺省 1）


@dataclass(frozen=True)
class StatsSpec:
    pattern_lib_version: int
    living: tuple[str, ...]
    facade: tuple[str, ...]
    patterns: tuple[PatternSpec, ...]
    declared: dict             # DECLARED_KEYS 七键
    view_layer_samples: tuple[int, ...]
    doc_registry: tuple[tuple[str, str], ...]   # (label, path)
    facade_baseline: dict      # {carrier: {"as_of": str, "values": {truth_key: int}}}
    suppress: tuple[tuple[str, str, str], ...]  # (pattern_id, file, note)


@dataclass
class TruthSet:
    fs: dict = field(default_factory=dict)          # 与 DECLARED_KEYS 同键
    hits: dict = field(default_factory=dict)        # samples / form2_total
    dis_range: tuple[int, int] = (0, 0)
    spec_dirs: set = field(default_factory=set)     # spec/ feature 目录名集合（清单比对用）
    view_layer_total: int = 0                       # 分桶表视图载体行求和（v1.1 口径）
    view_layer_pct: int = 0                         # floor(100 × total / form2_total)


# ---------------------------------------------------------------- 数字形态转换（纯函数）

_CN_DIGITS = {"零": 0, "一": 1, "二": 2, "三": 3, "四": 4,
              "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
_EN_DIGITS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
              "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}


def cn_to_int(s: str) -> int | None:
    """中文数字：零~九十九简单合成 + 双/两。非法返回 None。"""
    if s in ("双", "两"):
        return 2
    if s in _CN_DIGITS:
        return _CN_DIGITS[s]
    if s == "十":
        return 10
    m = re.fullmatch(r"([一二三四五六七八九])?十([一二三四五六七八九])?", s)
    if m:
        tens = _CN_DIGITS[m.group(1)] if m.group(1) else 1
        ones = _CN_DIGITS[m.group(2)] if m.group(2) else 0
        return tens * 10 + ones
    return None


def circled_to_int(ch: str) -> int | None:
    """带圈数字：①-⑳ U+2460-2473（1-20）、㉑-㉟ U+3251-325F（21-35）。"""
    if len(ch) != 1:
        return None
    cp = ord(ch)
    if 0x2460 <= cp <= 0x2473:
        return cp - 0x2460 + 1
    if 0x3251 <= cp <= 0x325F:
        return cp - 0x3251 + 21
    return None


def to_int(s: str) -> int | None:
    """统一值转换：阿拉伯 / 中文 / 带圈 / EN 小数字词。失败返回 None。"""
    s = s.strip()
    if RE_INT.match(s):
        return int(s)
    if len(s) == 1:
        v = circled_to_int(s)
        if v is not None:
            return v
    v = cn_to_int(s)
    if v is not None:
        return v
    if s.lower() in _EN_DIGITS:
        return _EN_DIGITS[s.lower()]
    return None


# ---------------------------------------------------------------- RS3 stats 块解析

def parse_stats_block(text: str) -> tuple[StatsSpec | None, list[CheckResult]]:
    """```stats 围栏恰一个 → JSON → schema 校验。结构性违规均 P1（rs-stats）。"""
    results: list[CheckResult] = []
    fences = RE_STATS_FENCE.findall(text)
    if len(fences) != 1:
        results.append(CheckResult(
            "rs-stats", CODE_WIKI_PATH, "P1",
            f"stats 块必须恰一个，实际 {len(fences)} 个"))
        return None, results
    try:
        data = json.loads(fences[0])
    except json.JSONDecodeError as e:
        results.append(CheckResult(
            "rs-stats", CODE_WIKI_PATH, "P1", f"stats 块 JSON 不可解析：{e}"))
        return None, results

    if not isinstance(data, dict):
        results.append(CheckResult("rs-stats", CODE_WIKI_PATH, "P1", "stats 块非 JSON 对象"))
        return None, results

    # carriers 两级非空互斥
    carriers = data.get("carriers")
    if (not isinstance(carriers, dict)
            or not isinstance(carriers.get("living"), list) or not isinstance(carriers.get("facade"), list)
            or not carriers["living"] or not carriers["facade"]):
        results.append(CheckResult(
            "rs-stats", CODE_WIKI_PATH, "P1", "carriers 两级（living/facade）必须为非空数组"))
        return None, results
    living = tuple(carriers["living"])
    facade = tuple(carriers["facade"])
    overlap = set(living) & set(facade)
    if overlap:
        results.append(CheckResult(
            "rs-stats", CODE_WIKI_PATH, "P1", f"carriers 两级互斥违规：{sorted(overlap)}"))
    all_carriers = set(living) | set(facade)

    # patterns：非空 + regex 可编译 + truth ∈ 绑定集 + scope ⊆ 载体集
    patterns: list[PatternSpec] = []
    raw_patterns = data.get("patterns")
    if not isinstance(raw_patterns, list) or not raw_patterns:
        results.append(CheckResult("rs-stats", CODE_WIKI_PATH, "P1", "patterns 必须为非空数组"))
    else:
        for p in raw_patterns:
            pid = p.get("id", "?")
            if not isinstance(p, dict) or "regex" not in p or "truth" not in p:
                results.append(CheckResult(
                    "rs-stats", CODE_WIKI_PATH, "P1", f"pattern {pid} 缺 regex/truth 字段"))
                continue
            try:
                rx = re.compile(p["regex"])
            except re.error as e:
                results.append(CheckResult(
                    "rs-stats", CODE_WIKI_PATH, "P1", f"pattern {pid} regex 不可编译：{e}"))
                continue
            keys = p["truth"].split("|")
            bad = [k for k in keys if k not in TRUTH_KEYS]
            if bad:
                results.append(CheckResult(
                    "rs-stats", CODE_WIKI_PATH, "P1",
                    f"pattern {pid} truth 越界：{bad}（绑定集封闭枚举）"))
                continue
            scope = tuple(p.get("scope", ()))
            bad_scope = [s for s in scope if s not in all_carriers]
            if bad_scope:
                results.append(CheckResult(
                    "rs-stats", CODE_WIKI_PATH, "P1",
                    f"pattern {pid} scope 越界：{bad_scope}"))
                continue
            group = int(p.get("group", 1))
            if group < 1 or group > rx.groups:
                results.append(CheckResult(
                    "rs-stats", CODE_WIKI_PATH, "P1",
                    f"pattern {pid} group={group} 超出捕获组数 {rx.groups}"))
                continue
            patterns.append(PatternSpec(pid, rx, p["truth"], scope, group))

    # declared 七键齐
    declared = data.get("declared", {})
    if not isinstance(declared, dict):
        results.append(CheckResult("rs-stats", CODE_WIKI_PATH, "P1", "declared 必须为对象"))
        declared = {}
    for k in DECLARED_KEYS:
        if k not in declared:
            results.append(CheckResult(
                "rs-stats", CODE_WIKI_PATH, "P1", f"declared 缺键：{k}"))
        elif not isinstance(declared[k], int) or declared[k] < 0:
            results.append(CheckResult(
                "rs-stats", CODE_WIKI_PATH, "P1", f"declared.{k} 必须为非负整数"))

    # view_layer_samples：正 int 列表（追溯性声明，非求和基础——v1.1）
    vls = data.get("view_layer_samples", [])
    if not isinstance(vls, list) or any(not isinstance(v, int) or v <= 0 for v in vls):
        results.append(CheckResult(
            "rs-stats", CODE_WIKI_PATH, "P1", "view_layer_samples 必须为正整数数组"))

    # doc_registry：(label, path)
    doc_registry: list[tuple[str, str]] = []
    for entry in data.get("doc_registry", []):
        if not isinstance(entry, dict) or "label" not in entry or "path" not in entry:
            results.append(CheckResult(
                "rs-stats", CODE_WIKI_PATH, "P1", "doc_registry 条目缺 label/path"))
            continue
        doc_registry.append((entry["label"], entry["path"]))

    # facade_baseline：键 ⊆ 载体集（含 facade；历史允许 living 无基准）
    baseline = data.get("facade_baseline", {})
    if not isinstance(baseline, dict):
        results.append(CheckResult("rs-stats", CODE_WIKI_PATH, "P1", "facade_baseline 必须为对象"))
        baseline = {}
    for carrier, blk in baseline.items():
        if carrier not in all_carriers:
            results.append(CheckResult(
                "rs-stats", CODE_WIKI_PATH, "P1", f"facade_baseline 键 {carrier} 不在载体集"))
        elif not isinstance(blk, dict) or "as_of" not in blk or not isinstance(blk.get("values"), dict):
            results.append(CheckResult(
                "rs-stats", CODE_WIKI_PATH, "P1", f"facade_baseline.{carrier} 缺 as_of/values"))

    # suppress：(pattern_id, file, note)
    suppress: list[tuple[str, str, str]] = []
    for entry in data.get("suppress", []):
        if (not isinstance(entry, dict) or "pattern_id" not in entry
                or "file" not in entry or "note" not in entry):
            results.append(CheckResult(
                "rs-stats", CODE_WIKI_PATH, "P1", "suppress 条目缺 pattern_id/file/note"))
            continue
        suppress.append((entry["pattern_id"], entry["file"], entry["note"]))

    if results:
        return None, results
    spec = StatsSpec(
        pattern_lib_version=data.get("pattern_lib_version", 1),
        living=living, facade=facade, patterns=tuple(patterns),
        declared={k: declared[k] for k in DECLARED_KEYS if k in declared},
        view_layer_samples=tuple(vls),
        doc_registry=tuple(doc_registry),
        facade_baseline=baseline,
        suppress=tuple(suppress),
    )
    return spec, results


# ---------------------------------------------------------------- RS2 真值枚举器

def _read(path: str) -> str | None:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except OSError:
        return None


def _count_md_files(root: str, rel_dir: str) -> int:
    d = os.path.join(root, rel_dir)
    if not os.path.isdir(d):
        return -1
    return sum(1 for n in os.listdir(d) if n.endswith(".md") and os.path.isfile(os.path.join(d, n)))


def build_truth_set(spec: StatsSpec, root: str) -> tuple[TruthSet, list[CheckResult]]:
    """七通道枚举（T1-T7）。真值源损坏产声波式 P1（rs-truth）。"""
    results: list[CheckResult] = []
    truth = TruthSet()

    # T1: spec feature 目录（排除 templates）
    spec_dir = os.path.join(root, SPEC_DIR)
    if not os.path.isdir(spec_dir):
        results.append(CheckResult("rs-truth", SPEC_DIR + "/", "P1", "spec/ 目录缺失"))
        truth.fs["spec_feature_dirs"] = -1
    else:
        names = {n for n in os.listdir(spec_dir)
                 if n != "templates" and os.path.isdir(os.path.join(spec_dir, n))}
        truth.spec_dirs = names
        truth.fs["spec_feature_dirs"] = len(names)

    # T2: 文件计数四通道
    truth.fs["adr_files"] = _count_md_files(root, "adr")
    truth.fs["dev_logs"] = _count_md_files(root, "docs/dev-log")
    scripts_dir = os.path.join(root, "scripts")
    truth.fs["scripts"] = (sum(1 for n in os.listdir(scripts_dir)
                               if n.endswith(".py") and os.path.isfile(os.path.join(scripts_dir, n)))
                           if os.path.isdir(scripts_dir) else -1)
    truth.fs["templates"] = _count_md_files(root, "spec/templates")
    for k, v in truth.fs.items():
        if v == -1:
            results.append(CheckResult("rs-truth", k, "P1", f"真值目录缺失（{k} 计数为 -1）"))

    # T3: hooks
    hooks_text = _read(os.path.join(root, HOOKS_PATH))
    if hooks_text is None:
        results.append(CheckResult("rs-truth", HOOKS_PATH, "P1", ".pre-commit-config.yaml 不可读"))
        truth.fs["hooks"] = -1
    else:
        truth.fs["hooks"] = sum(1 for line in hooks_text.splitlines() if RE_HOOK_ID.match(line))

    # T4: PROGRESS P-号
    prog_text = _read(os.path.join(root, PROGRESS_PATH))
    if prog_text is None:
        results.append(CheckResult("rs-truth", PROGRESS_PATH, "P1", "PROGRESS.md 不可读"))
        truth.fs["progress_tasks"] = -1
    else:
        truth.fs["progress_tasks"] = sum(1 for line in prog_text.splitlines()
                                         if RE_P_TASK.match(line))

    # T5: hits 直读（M7 唯一活载体，m7_stats 看护其准确性）
    m7_text = _read(os.path.join(root, M7_PATH))
    if m7_text is None:
        results.append(CheckResult("rs-truth", M7_PATH, "P1", "M7_EVIDENCE_LOG.md 不可读"))
    else:
        hits_fences = RE_HITS_FENCE.findall(m7_text)
        if len(hits_fences) != 1:
            results.append(CheckResult(
                "rs-truth", M7_PATH, "P1", f"hits 块必须恰一个，实际 {len(hits_fences)} 个（消费前提）"))
        else:
            try:
                hits = json.loads(hits_fences[0])
                truth.hits["samples"] = hits["samples"]
                truth.hits["form2_total"] = hits["form2_total"]
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                results.append(CheckResult(
                    "rs-truth", M7_PATH, "P1", f"hits 块不可解析：{e}（真值源坏 ≠ 校验通过）"))

    # T6: DIS 编号范围
    dis_text = _read(os.path.join(root, DIS_PATH))
    if dis_text is None:
        results.append(CheckResult("rs-truth", DIS_PATH, "P1", "discoveries/README.md 不可读"))
    else:
        ids = [int(x) for x in RE_DIS_ID.findall(dis_text)]
        if ids:
            truth.dis_range = (min(ids), max(ids))
        else:
            results.append(CheckResult("rs-truth", DIS_PATH, "P1", "discoveries 无 DIS 编号"))

    # T7: 视图载体行求和（v1.1 口径：分桶表载体列匹配视图载体模式的行小计求和）
    if m7_text is not None:
        section = _extract_section(m7_text, RE_S2_HEADER)
        if section is None:
            results.append(CheckResult("rs-truth", M7_PATH, "P1", "M7 §2 分桶节缺失"))
        else:
            total = 0
            ok = True
            for line in section.splitlines():
                if not RE_BUCKET_ROW.match(line):
                    continue
                cells = [c.strip() for c in line.split("|")]
                if len(cells) < 4:      # "| 载体 | … | 小计 |" 最少 4 段（首尾空串）
                    continue
                carrier_cell = cells[1].replace("*", "")
                if carrier_cell == "合计" or not RE_VIEW_CARRIER.search(carrier_cell):
                    continue
                sub = cells[-2].replace("*", "")
                if RE_INT.match(sub):
                    total += int(sub)
                else:
                    ok = False
            if ok:
                truth.view_layer_total = total
                f2t = truth.hits.get("form2_total")
                if isinstance(f2t, int) and f2t > 0:
                    truth.view_layer_pct = 100 * total // f2t
            else:
                results.append(CheckResult(
                    "rs-truth", M7_PATH, "P1", "视图载体行小计列存在非整数值（T7 中止）"))
    return truth, results


def _extract_section(text: str, header_re: re.Pattern) -> str | None:
    """header_re 起到下一个 ## N. 节（或文尾）。"""
    m = header_re.search(text)
    if not m:
        return None
    rest = text[m.start():]
    nxt = re.search(r"^##\s+\d", rest[1:], re.M)
    return rest if nxt is None else rest[:nxt.start() + 1]


# ---------------------------------------------------------------- RS4 对账引擎

def _truth_value(truth: TruthSet, key: str):
    if key.startswith("fs."):
        return truth.fs.get(key.split(".", 1)[1])
    if key.startswith("hits."):
        return truth.hits.get(key.split(".", 1)[1])
    if key == "dis.range_min":
        return truth.dis_range[0]
    if key == "dis.range_max":
        return truth.dis_range[1]
    if key == "derived.view_layer_total":
        return truth.view_layer_total
    if key == "derived.view_layer_pct":
        return truth.view_layer_pct
    return None


def _suppressed(spec: StatsSpec, pid: str, file: str) -> bool:
    return any(s_pid == pid and s_file == file for s_pid, s_file, _ in spec.suppress)


def _scan_lines(lines: list[str], patterns: tuple[PatternSpec, ...], truth: TruthSet,
                carrier: str, severity: str, spec: StatsSpec) -> list[CheckResult]:
    """逐行状态机：机读四类围栏内跳过，其余行逐模式比对（行号保真，IMPL §3.4 裁定）。"""
    results: list[CheckResult] = []
    in_fence = False
    for lineno, line in enumerate(lines, 1):
        stripped = line.strip()
        if in_fence:
            if stripped == "```":
                in_fence = False
            continue
        if MACHINE_FENCE_OPEN.match(stripped):
            in_fence = True
            continue
        for pat in patterns:
            if pat.scope and carrier not in pat.scope:
                continue
            for m in pat.regex.finditer(line):
                if _suppressed(spec, pat.pid, carrier):
                    continue
                keys = pat.truth.split("|")
                groups = m.groups()
                for i, key in enumerate(keys):
                    if len(keys) == 1:
                        raw = groups[pat.group - 1] if pat.group <= len(groups) else None
                    else:
                        raw = groups[i] if i < len(groups) else None
                    if raw is None:
                        results.append(CheckResult(
                            "rs-pattern", carrier, severity,
                            f"pattern {pat.pid} 捕获组越界（group={pat.group}）", lineno))
                        continue
                    val = to_int(raw)
                    expected = _truth_value(truth, key)
                    if val is None:
                        results.append(CheckResult(
                            "rs-pattern", carrier, severity,
                            f"pattern {pat.pid} 捕获值「{raw}」不可转换为数字", lineno))
                    elif expected is None:
                        results.append(CheckResult(
                            "rs-pattern", carrier, severity,
                            f"pattern {pat.pid} truth {key} 无真值（真值源损坏前置 P1）", lineno))
                    elif val != expected:
                        results.append(CheckResult(
                            "rs-pattern", carrier, severity,
                            f"pattern {pat.pid} 命中值 {val} ≠ 真值 {expected}（{key}）", lineno))
    return results


def _scan_facade_baseline(lines: list[str], spec: StatsSpec, truth: TruthSet,
                          carrier: str) -> list[CheckResult]:
    """facade 载体：命中值 vs baseline 声明值（P3）；baseline vs 当前真值滞后提示（P3）。"""
    results: list[CheckResult] = []
    baseline = spec.facade_baseline.get(carrier)
    if baseline is None:
        return results
    values = baseline.get("values", {})
    as_of = baseline.get("as_of", "?")

    for pat in spec.patterns:
        if pat.scope and carrier not in pat.scope:
            continue
        if len(pat.truth.split("|")) != 1:
            continue  # 双键模式不适用 facade 基准比对
        key = pat.truth
        if key not in values:
            continue
        base_val = values[key]
        in_fence = False
        for lineno, line in enumerate(lines, 1):
            stripped = line.strip()
            if in_fence:
                if stripped == "```":
                    in_fence = False
                continue
            if MACHINE_FENCE_OPEN.match(stripped):
                in_fence = True
                continue
            for m in pat.regex.finditer(line):
                if _suppressed(spec, pat.pid, carrier):
                    continue
                raw = m.group(pat.group) if pat.group <= len(m.groups()) else None
                if raw is None:
                    continue
                val = to_int(raw)
                if val is not None and val != base_val:
                    results.append(CheckResult(
                        "rs-pattern", carrier, "P3",
                        f"pattern {pat.pid} 命中值 {val} ≠ 基准 {base_val}（prose 与基准漂移）",
                        lineno))
    # baseline vs 当前真值（每键一条滞后提示，去重）
    for key, base_val in values.items():
        cur = _truth_value(truth, key)
        if cur is not None and base_val != cur:
            results.append(CheckResult(
                "rs-pattern", carrier, "P3",
                f"快照滞后：基准 {key}={base_val}（as_of={as_of}）≠ 当前真值 {cur}——择机刷新"))
    return results


def _scan_svg(svg_text: str, spec: StatsSpec, truth: TruthSet,
              carrier: str) -> list[CheckResult]:
    """SVG 载体：不走 prose 模式——baseline values 的 >N< 文本节点包含性检查（DESIGN §4.3 原则③）。"""
    results: list[CheckResult] = []
    baseline = spec.facade_baseline.get(carrier)
    if baseline is None:
        return results
    as_of = baseline.get("as_of", "?")
    for key, base_val in baseline.get("values", {}).items():
        node = f">{base_val}<"
        if node not in svg_text:
            results.append(CheckResult(
                "rs-pattern", carrier, "P3",
                f"SVG 缺基准文本节点 {node}（{key}，基准 {base_val}）——prose/图形与基准漂移"))
        cur = _truth_value(truth, key)
        if cur is not None and base_val != cur:
            results.append(CheckResult(
                "rs-pattern", carrier, "P3",
                f"快照滞后：基准 {key}={base_val}（as_of={as_of}）≠ 当前真值 {cur}——择机刷新"))
    return results


def _extract_tree_spec_dirs(wiki_text: str) -> list[str]:
    """§2 树内 spec/ 段条目（4 空格缩进；条目名取 / 前首段）。"""
    dirs: list[str] = []
    in_spec = False
    for line in wiki_text.splitlines():
        if RE_TREE_SPEC.match(line):
            in_spec = True
            continue
        if not in_spec:
            continue
        m = RE_TREE_ENTRY.match(line)
        if m:
            dirs.append(m.group(1).split("/")[0])
        elif line.strip():  # 非条目非空行 → 段结束（树围栏闭合/注释块等）
            break
    return dirs


def reconcile(spec: StatsSpec, truth: TruthSet, root: str) -> list[CheckResult]:
    """三路对账：① rs-decl（P1）② rs-pattern（living P2 / facade P3）③ rs-list（P2）。"""
    results: list[CheckResult] = []

    # ① rs-decl：declared vs 真值机械重数（I-6 第一级）
    for key, declared in spec.declared.items():
        actual = truth.fs.get(key)
        if actual is None:
            continue  # 真值源损坏已由 rs-truth P1 声波报告
        if declared != actual:
            results.append(CheckResult(
                "rs-decl", CODE_WIKI_PATH, "P1",
                f"declared.{key} 声明 {declared} ≠ 机械重数 {actual}",
                gap=f"意图(声明) {key}={declared} → 证据(重数) {actual} → 缺口 {'+' if actual > declared else ''}{actual - declared}（{'欠声明' if actual > declared else '过声明'}）"))

    # ② rs-pattern：逐载体扫描
    for carrier in spec.living:
        text = _read(os.path.join(root, carrier))
        if text is None:
            results.append(CheckResult(
                "rs-stats", carrier, "P1", "living 载体文件缺失（声明了载体但不存在）"))
            continue
        results.extend(_scan_lines(text.splitlines(), spec.patterns, truth,
                                   carrier, "P2", spec))
    for carrier in spec.facade:
        path = os.path.join(root, carrier)
        text = _read(path)
        if text is None:
            results.append(CheckResult(
                "rs-stats", carrier, "P1", "facade 载体文件缺失（声明了载体但不存在）"))
            continue
        if carrier.endswith(".svg"):
            results.extend(_scan_svg(text, spec, truth, carrier))
        else:
            results.extend(_scan_facade_baseline(text.splitlines(), spec, truth, carrier))

    # ③ rs-list：树/索引/版本
    wiki_text = _read(os.path.join(root, CODE_WIKI_PATH))
    if wiki_text is not None:
        results.extend(_reconcile_lists(spec, truth, root, wiki_text))
    return results


def _reconcile_lists(spec: StatsSpec, truth: TruthSet, root: str,
                     wiki_text: str) -> list[CheckResult]:
    results: list[CheckResult] = []

    # 树 spec/ 子目录集 vs LS（缺登/幻影双向）
    tree_dirs = set(_extract_tree_spec_dirs(wiki_text))
    if truth.spec_dirs:
        missing = truth.spec_dirs - tree_dirs
        phantom = tree_dirs - truth.spec_dirs - {"templates"}
        if missing:
            results.append(CheckResult(
                "rs-list", CODE_WIKI_PATH, "P2",
                f"§2.1 树缺登 spec/ 子目录：{sorted(missing)}",
                gap=f"意图(树登记集) {sorted(tree_dirs)} → 证据(LS 实际) {sorted(truth.spec_dirs)} → 缺口 缺登 {sorted(missing)}"))
        if phantom:
            results.append(CheckResult(
                "rs-list", CODE_WIKI_PATH, "P2",
                f"§2.1 树幻影子目录（LS 不存在）：{sorted(phantom)}",
                gap=f"意图(树登记集) {sorted(tree_dirs)} → 证据(LS 实际) {sorted(truth.spec_dirs)} → 缺口 幻影 {sorted(phantom)}"))

    # §9 spec 索引链接集 vs LS（缺行/幻影行）
    s9 = _extract_section(wiki_text, RE_S9_HEADER)
    if s9 is not None:
        s9_dirs = set(RE_S9_SPEC_LINK.findall(s9))
        if truth.spec_dirs:
            missing = truth.spec_dirs - s9_dirs
            phantom = s9_dirs - truth.spec_dirs
            if missing:
                results.append(CheckResult(
                    "rs-list", CODE_WIKI_PATH, "P2",
                    f"§9 索引缺 spec/*/ 行：{sorted(missing)}",
                    gap=f"意图(§9 索引集) {sorted(s9_dirs)} → 证据(LS 实际) {sorted(truth.spec_dirs)} → 缺口 缺行 {sorted(missing)}"))
            if phantom:
                results.append(CheckResult(
                    "rs-list", CODE_WIKI_PATH, "P2",
                    f"§9 索引幻影行（LS 不存在）：{sorted(phantom)}",
                    gap=f"意图(§9 索引集) {sorted(s9_dirs)} → 证据(LS 实际) {sorted(truth.spec_dirs)} → 缺口 幻影 {sorted(phantom)}"))

        # doc_registry 版本对账（§9 载体行版本号 vs front-matter version，字符串全等）
        # 行定位 = 链接形态（](./rel) 文件链接或 ](./dir/) 父目录链接）——
        # label 子串会误命中叙事行（如 dev-log 行「002（cpp-hub-absorption）」），F20
        if s9 is not None:
            for label, rel in spec.doc_registry:
                rel_dir = os.path.dirname(rel)
                link_tokens = [f"](./{rel})"]
                if rel_dir:
                    link_tokens.append(f"](./{rel_dir}/)")
                line_found = None
                for line in s9.splitlines():
                    if any(tok in line for tok in link_tokens):
                        line_found = line
                        break
                if line_found is None:
                    results.append(CheckResult(
                        "rs-list", CODE_WIKI_PATH, "P2",
                        f"doc_registry「{label}」在 §9 无对应行"))
                    continue
                vm = RE_VERSION_TOKEN.search(line_found)
                if vm is None:
                    results.append(CheckResult(
                        "rs-list", CODE_WIKI_PATH, "P2",
                        f"doc_registry「{label}」§9 行无版本号 token"))
                    continue
                prose_ver = vm.group(1)
                doc_text = _read(os.path.join(root, rel))
                if doc_text is None:
                    results.append(CheckResult(
                        "rs-truth", rel, "P1", f"doc_registry 文档不可读：{rel}"))
                    continue
                fm = RE_FM_VERSION.search(doc_text)
                if fm is None:
                    results.append(CheckResult(
                        "rs-truth", rel, "P1", f"doc_registry 文档无 front-matter version：{rel}"))
                    continue
                if prose_ver != fm.group(1):
                    results.append(CheckResult(
                        "rs-list", CODE_WIKI_PATH, "P2",
                        f"「{label}」§9 版本 v{prose_ver} ≠ front-matter {fm.group(1)}",
                        gap=f"意图(§9 行声明) v{prose_ver} → 证据(front-matter) v{fm.group(1)} → 缺口 版本失配 {label}"))
    return results


# ---------------------------------------------------------------- RS5 selftest

def _mini_stats_json(**overrides) -> str:
    data = {
        "pattern_lib_version": 1,
        "carriers": {
            "living": ["CODE_WIKI.md", "docs/discoveries/README.md"],
            "facade": ["README.md", "assets/evidence.svg"],
        },
        "patterns": [
            {"id": "PT-A", "regex": "形态 II [^。\\n；]{0,20}?(\\d+) 处", "truth": "hits.form2_total"},
            {"id": "PT-B", "regex": "样本①-([①-㉟])", "truth": "hits.samples"},
            {"id": "PT-C", "regex": "([一二三四五六七八九十双两]|\\d+) feature 目录", "truth": "fs.spec_feature_dirs"},
            {"id": "PT-D", "regex": "(双|两|三) hook", "truth": "fs.hooks"},
            {"id": "PT-E", "regex": "dev-log ×(\\d+)", "truth": "fs.dev_logs"},
            {"id": "PT-F", "regex": "ADR-(\\d{4})~(\\d{4})\\s*(\\S+?)份", "truth": "fs.adr_files", "group": 3},
            {"id": "PT-G", "regex": "视图层合计 (\\d+) 处", "truth": "derived.view_layer_total"},
            {"id": "PT-H", "regex": "占形态 II 总量 (\\d+)%", "truth": "derived.view_layer_pct"},
            {"id": "PT-I", "regex": "P-(\\d{3})~P-(\\d{3})", "truth": "fs.progress_tasks", "group": 2},
        ],
        "declared": {
            "spec_feature_dirs": 2, "adr_files": 2, "dev_logs": 1, "scripts": 1,
            "templates": 1, "hooks": 2, "progress_tasks": 3,
        },
        "view_layer_samples": [1, 2],
        "doc_registry": [{"label": "框架", "path": "docs/FRAME.md"}],
        "facade_baseline": {
            "README.md": {"as_of": "2026-08-22", "values": {"hits.samples": 3, "hits.form2_total": 9}},
            "assets/evidence.svg": {"as_of": "2026-08-22", "values": {"hits.samples": 3, "hits.form2_total": 9}},
        },
        "suppress": [],
    }
    data.update(overrides)
    return json.dumps(data, ensure_ascii=False, indent=2)


MINI_WIKI_BODY = """# Mini Wiki

## 2. 整体架构

```
root/
└── spec/
    ├── templates/
    ├── alpha/
    └── beta/
```

## 9. 文档索引

| 文件 | 定位 |
|------|------|
| [spec/alpha/](./spec/alpha/) | alpha |
| [spec/beta/](./spec/beta/) | beta |
| [docs/FRAME.md](./docs/FRAME.md) | 框架 v1.0 |

当前态：样本①-③，形态 II 9 处；spec/ 两 feature 目录；双 hook；dev-log ×1；ADR-0001~0002 两份；P-001~P-003。
视图层合计 5 处，占形态 II 总量 55%。

## 10. 机读声明块（stats）

```stats
{stats}
```
"""

MINI_M7 = """# Mini M7

## 1. 样本登记表

| # | 日期 | 载体 | 审查配置 | 发现 | 形态II复发 | 来源 |
|---|------|------|---------|------|-----------|------|
| 1 | 2026-08-01 | CODE_WIKI v1 | 自查 | 1 P3 | 3 | 本轮 |
| 2 | 2026-08-02 | OTHER | 自查 | 1 P3 | 2 | 本轮 |
| 3 | 2026-08-03 | CODE_WIKI v2 | 自查 | 1 P3 | 2 | 本轮 |

## 2. 形态 II 复发分桶（载体 × 字段类型）

| 载体 \\ 字段类型 | 版本号 | 计数 | 小计 |
|---|---|---|---|
| CODE_WIKI v1（本仓，视图批） | — | 3 | 3 |
| OTHER（本仓，非视图） | — | 2 | 2 |
| CODE_WIKI v2（本仓，视图批） | — | 2 | 2 |
| **合计** | 0 | 7 | **7** |

## 5. 机读统计块（hits）

```hits
{
  "samples": 3,
  "form2_by_field": {"version": 0, "count": 7},
  "form2_total": 9,
  "form2_pre_ledger": 2,
  "form2_from_samples": 7,
  "findings": {"p1": 0, "p2": 0, "p3": 3, "unlabeled": 0, "cells_nonstandard": 0}
}
```
"""

MINI_DIS = """# Mini Discoveries

| DIS | 主题 | 状态 |
|-----|------|------|
| DIS-001 | a | resolved |
| DIS-002 | b | open |
"""

MINI_PROGRESS = """# Mini Progress

| P | 任务 | 状态 |
|---|------|------|
| P-001 | a | done |
| P-002 | b | done |
| P-003 | c | in-progress |
"""

MINI_HOOKS = """repos:
  - repo: local
    hooks:
      - id: hook-a
        entry: python scripts/a.py
      - id: hook-b
        entry: python scripts/b.py
"""

MINI_FRAME = """---
id: frame
type: framework
version: 1.0
---

# Mini Frame
"""

MINI_README = """# Mini README

门面快照：样本①-③，形态 II 9 处（时点 2026-08-22）。
"""

MINI_SVG = """<svg><text>3</text><text>9</text></svg>
"""


def _build_mini_repo(base: str, stats_json: str | None = None,
                     wiki_body: str | None = None) -> str:
    """构造迷你仓（tempdir 下）；返回 root。stats_json/wiki_body 支持逐 fixture 变体。"""
    root = tempfile.mkdtemp(prefix="repo_stats_selftest_")
    os.makedirs(os.path.join(root, "spec", "templates"), exist_ok=True)
    os.makedirs(os.path.join(root, "spec", "alpha"), exist_ok=True)
    os.makedirs(os.path.join(root, "spec", "beta"), exist_ok=True)
    os.makedirs(os.path.join(root, "adr"), exist_ok=True)
    os.makedirs(os.path.join(root, "docs", "dev-log"), exist_ok=True)
    os.makedirs(os.path.join(root, "docs", "discoveries"), exist_ok=True)
    os.makedirs(os.path.join(root, "scripts"), exist_ok=True)
    os.makedirs(os.path.join(root, "assets"), exist_ok=True)

    with open(os.path.join(root, "spec", "templates", "T.md"), "w", encoding="utf-8") as f:
        f.write("# t\n")
    with open(os.path.join(root, "adr", "ADR-0001.md"), "w", encoding="utf-8") as f:
        f.write("# a\n")
    with open(os.path.join(root, "adr", "ADR-0002.md"), "w", encoding="utf-8") as f:
        f.write("# b\n")
    with open(os.path.join(root, "docs", "dev-log", "DEV-LOG-001.md"), "w", encoding="utf-8") as f:
        f.write("# d\n")
    with open(os.path.join(root, "scripts", "tool.py"), "w", encoding="utf-8") as f:
        f.write("# tool\n")

    body = wiki_body if wiki_body is not None else MINI_WIKI_BODY
    stats = stats_json if stats_json is not None else _mini_stats_json()
    with open(os.path.join(root, "CODE_WIKI.md"), "w", encoding="utf-8") as f:
        f.write(body.replace("{stats}", stats))
    with open(os.path.join(root, "docs", "M7_EVIDENCE_LOG.md"), "w", encoding="utf-8") as f:
        f.write(MINI_M7)
    with open(os.path.join(root, "docs", "discoveries", "README.md"), "w", encoding="utf-8") as f:
        f.write(MINI_DIS)
    with open(os.path.join(root, "docs", "PROGRESS.md"), "w", encoding="utf-8") as f:
        f.write(MINI_PROGRESS)
    with open(os.path.join(root, ".pre-commit-config.yaml"), "w", encoding="utf-8") as f:
        f.write(MINI_HOOKS)
    with open(os.path.join(root, "docs", "FRAME.md"), "w", encoding="utf-8") as f:
        f.write(MINI_FRAME)
    with open(os.path.join(root, "README.md"), "w", encoding="utf-8") as f:
        f.write(MINI_README)
    with open(os.path.join(root, "assets", "evidence.svg"), "w", encoding="utf-8") as f:
        f.write(MINI_SVG)
    _ = base
    return root


def _verify(root: str) -> tuple[Summary, StatsSpec | None]:
    wiki_text = _read(os.path.join(root, CODE_WIKI_PATH)) or ""
    spec, r0 = parse_stats_block(wiki_text)
    results = list(r0)
    if spec is not None:
        truth, r1 = build_truth_set(spec, root)
        results.extend(r1)
        results.extend(reconcile(spec, truth, root))
    return Summary(results), spec


def _expect(name: str, cond: bool, failures: list[str]) -> int:
    if not cond:
        failures.append(name)
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
    return 1


def run_selftest() -> int:
    """27 fixture（20 基 + F7 双变体 + F21-F24 drift-gate 缺口报告）+ I-1 只读断言 + 数字转换全区间
    （expect 计数自增机械计数，DR-6 同构）。"""
    failures: list[str] = []
    passed = 0
    total = 0

    def check(name, cond):
        nonlocal passed, total
        total += 1
        passed += _expect(name, cond, failures)

    print("repo_stats selftest:")

    # F12: 数字转换全区间（中文一~九十九 + 带圈 1-35 + EN/双两）
    cn_ok = all(cn_to_int(s) == v for s, v in
                [("一", 1), ("九", 9), ("十", 10), ("十一", 11), ("十九", 19),
                 ("二十", 20), ("二十一", 21), ("五十三", 53), ("九十九", 99),
                 ("双", 2), ("两", 2)])
    cn_bad = cn_to_int("百") is None and cn_to_int("") is None
    circ_ok = True
    for i in range(1, 36):
        ch = chr(0x2460 + i - 1) if i <= 20 else chr(0x3251 + i - 21)
        if circled_to_int(ch) != i:
            circ_ok = False
            break
    circ_bad = circled_to_int("a") is None and circled_to_int("①①") is None
    en_ok = to_int("Six") == 6 and to_int("ten") == 10
    check("F12 数字转换全区间（中文/带圈/EN）", cn_ok and cn_bad and circ_ok and circ_bad and en_ok)

    # F1: 合规迷你仓全绿 + TruthSet 精确断言
    root = _build_mini_repo("")
    summary, spec = _verify(root)
    t_ok = False
    if spec is not None:
        truth, _ = build_truth_set(spec, root)
        t_ok = (truth.fs["spec_feature_dirs"] == 2 and truth.fs["adr_files"] == 2
                and truth.fs["dev_logs"] == 1 and truth.fs["scripts"] == 1
                and truth.fs["templates"] == 1 and truth.fs["hooks"] == 2
                and truth.fs["progress_tasks"] == 3
                and truth.hits["samples"] == 3 and truth.hits["form2_total"] == 9
                and truth.dis_range == (1, 2)
                and truth.view_layer_total == 5 and truth.view_layer_pct == 55)
    check("F1 合规迷你仓 exit 0 + TruthSet 精确断言", summary.passed and t_ok)
    shutil.rmtree(root, ignore_errors=True)

    # F2: stats 块缺失
    root = _build_mini_repo("", wiki_body=MINI_WIKI_BODY.split("## 10.")[0])
    summary, _ = _verify(root)
    p1 = [r for r in summary.results if r.severity == "P1" and "恰一个" in r.message]
    check("F2 stats 块缺失 → P1", len(p1) == 1 and not summary.passed)
    shutil.rmtree(root, ignore_errors=True)

    # F3: stats 块 JSON 非法
    root = _build_mini_repo("", stats_json="{not json")
    summary, _ = _verify(root)
    p1 = [r for r in summary.results if r.severity == "P1" and "JSON" in r.message]
    check("F3 stats 块 JSON 非法 → P1", len(p1) == 1 and not summary.passed)
    shutil.rmtree(root, ignore_errors=True)

    # F4: patterns schema 违规（truth 越界）
    bad = json.loads(_mini_stats_json())
    bad["patterns"] = [{"id": "PT-X", "regex": r"(\d+)", "truth": "fs.nonexistent"}]
    root = _build_mini_repo("", stats_json=json.dumps(bad, ensure_ascii=False))
    summary, _ = _verify(root)
    p1 = [r for r in summary.results if r.severity == "P1" and "truth 越界" in r.message]
    check("F4 patterns truth 越界 → P1", len(p1) == 1 and not summary.passed)
    shutil.rmtree(root, ignore_errors=True)

    # F5: declared 失配（rs-decl P1 + declared/actual 报文）
    bad = json.loads(_mini_stats_json())
    bad["declared"]["spec_feature_dirs"] = 9
    root = _build_mini_repo("", stats_json=json.dumps(bad, ensure_ascii=False))
    summary, _ = _verify(root)
    p1 = [r for r in summary.results
          if r.severity == "P1" and "声明 9 ≠ 机械重数 2" in r.message]
    check("F5 declared 失配 → P1（declared/actual）", len(p1) == 1 and not summary.passed)
    shutil.rmtree(root, ignore_errors=True)

    # F6: living 命中值 ≠ 真值 → P2 + 行号
    wiki = MINI_WIKI_BODY.replace("形态 II 9 处", "形态 II 8 处")
    root = _build_mini_repo("", wiki_body=wiki)
    summary, _ = _verify(root)
    p2 = [r for r in summary.results
          if r.severity == "P2" and "PT-A" in r.message and r.line is not None]
    check("F6 living 命中值 ≠ 真值 → P2 + 行号", len(p2) >= 1 and not summary.passed)
    shutil.rmtree(root, ignore_errors=True)

    # F7: facade 命中值 ≠ baseline → P3 + exit 0（README prose 通道）
    root = _build_mini_repo("")
    with open(os.path.join(root, "README.md"), "w", encoding="utf-8") as f:
        f.write(MINI_README.replace("样本①-③", "样本①-②"))
    summary, _ = _verify(root)
    p3 = [r for r in summary.results
          if r.severity == "P3" and "README.md" in r.file and "基准 3" in r.message]
    check("F7 facade prose ≠ baseline → P3 + exit 0", len(p3) >= 1 and summary.passed)
    shutil.rmtree(root, ignore_errors=True)

    # F7b: SVG 通道（缺基准文本节点 → P3，非阻断）
    root = _build_mini_repo("")
    with open(os.path.join(root, "assets", "evidence.svg"), "w", encoding="utf-8") as f:
        f.write("<svg><text>2</text><text>9</text></svg>")
    summary, _ = _verify(root)
    p3 = [r for r in summary.results
          if r.severity == "P3" and "evidence.svg" in r.file and ">3<" in r.message]
    check("F7b SVG 缺基准文本节点 → P3 + exit 0", len(p3) >= 1 and summary.passed)
    shutil.rmtree(root, ignore_errors=True)

    # F7c: suppress 白名单（单匹配不跳 / 双匹配跳过）
    root = _build_mini_repo("")
    with open(os.path.join(root, "README.md"), "w", encoding="utf-8") as f:
        f.write(MINI_README.replace("样本①-③", "样本①-②"))
    bad = json.loads(_mini_stats_json())
    bad["suppress"] = [{"pattern_id": "PT-B", "file": "CODE_WIKI.md", "note": "单匹配（错文件）"}]
    with open(os.path.join(root, "CODE_WIKI.md"), "w", encoding="utf-8") as f:
        f.write(MINI_WIKI_BODY.replace("{stats}", json.dumps(bad, ensure_ascii=False, indent=2)))
    summary, _ = _verify(root)
    p3 = [r for r in summary.results
          if r.severity == "P3" and "README.md" in r.file and "PT-B" in r.message]
    single_not_skip = len(p3) == 1                       # 登记错文件 → README 漂移仍报
    bad["suppress"] = [{"pattern_id": "PT-B", "file": "README.md", "note": "双匹配"}]
    with open(os.path.join(root, "CODE_WIKI.md"), "w", encoding="utf-8") as f:
        f.write(MINI_WIKI_BODY.replace("{stats}", json.dumps(bad, ensure_ascii=False, indent=2)))
    summary, _ = _verify(root)
    p3 = [r for r in summary.results
          if r.severity == "P3" and "README.md" in r.file and "PT-B" in r.message]
    double_skip = len(p3) == 0 and summary.passed        # 双匹配 → 静默且无其他违规
    check("F7c suppress 单匹配不跳 / 双匹配跳过", single_not_skip and double_skip)
    shutil.rmtree(root, ignore_errors=True)

    # F8: baseline ≠ 当前真值 → P3 滞后 + exit 0
    bad = json.loads(_mini_stats_json())
    bad["facade_baseline"]["README.md"]["values"]["hits.samples"] = 2  # 真值 3 → 滞后
    root = _build_mini_repo("", stats_json=json.dumps(bad, ensure_ascii=False))
    summary, _ = _verify(root)
    p3 = [r for r in summary.results if r.severity == "P3" and "快照滞后" in r.message]
    check("F8 baseline 滞后 → P3 + exit 0", len(p3) >= 1 and summary.passed)
    shutil.rmtree(root, ignore_errors=True)

    # F9: §2.1 树缺登/幻影 → P2 双向（beta 行末位是 └ 非 ├）
    wiki = MINI_WIKI_BODY.replace("    ├── alpha/\n    └── beta/\n", "    └── alpha/\n")  # 树缺登 beta
    root = _build_mini_repo("", wiki_body=wiki)
    summary, _ = _verify(root)
    p2 = [r for r in summary.results if r.severity == "P2" and "树缺登" in r.message
          and "beta" in r.message]
    check("F9 树缺登 → P2", len(p2) == 1 and not summary.passed)
    shutil.rmtree(root, ignore_errors=True)

    # F10: §9 索引缺行/幻影行 → P2
    wiki = MINI_WIKI_BODY.replace("| [spec/beta/](./spec/beta/) | beta |\n", "")
    root = _build_mini_repo("", wiki_body=wiki)
    summary, _ = _verify(root)
    p2 = [r for r in summary.results if r.severity == "P2" and "§9 索引缺" in r.message]
    check("F10 §9 索引缺行 → P2", len(p2) == 1 and not summary.passed)
    shutil.rmtree(root, ignore_errors=True)

    # F11: doc_registry 版本失配（v1.0 vs 1.1）
    wiki = MINI_WIKI_BODY.replace("框架 v1.0", "框架 v1.1")
    root = _build_mini_repo("", wiki_body=wiki)
    summary, _ = _verify(root)
    p2 = [r for r in summary.results
          if r.severity == "P2" and "v1.1 ≠ front-matter 1.0" in r.message]
    check("F11 版本声明失配 → P2", len(p2) == 1 and not summary.passed)
    shutil.rmtree(root, ignore_errors=True)

    # F13: hits 块缺失 → 声波式 P1
    root = _build_mini_repo("")
    with open(os.path.join(root, "docs", "M7_EVIDENCE_LOG.md"), "w", encoding="utf-8") as f:
        f.write(MINI_M7.split("## 5.")[0])
    summary, _ = _verify(root)
    p1 = [r for r in summary.results if r.severity == "P1" and "hits" in r.message]
    check("F13 hits 块缺失 → 声波式 P1", len(p1) >= 1 and not summary.passed)
    shutil.rmtree(root, ignore_errors=True)

    # F14: front-matter 不可解析 → P1
    root = _build_mini_repo("")
    with open(os.path.join(root, "docs", "FRAME.md"), "w", encoding="utf-8") as f:
        f.write("# no front-matter\n")
    summary, _ = _verify(root)
    p1 = [r for r in summary.results
          if r.severity == "P1" and "front-matter version" in r.message]
    check("F14 front-matter 缺失 → P1", len(p1) == 1 and not summary.passed)
    shutil.rmtree(root, ignore_errors=True)

    # F15: spec/ 目录缺失 → P1
    root = _build_mini_repo("")
    shutil.rmtree(os.path.join(root, "spec"))
    summary, _ = _verify(root)
    p1 = [r for r in summary.results if r.severity == "P1" and "spec/" in r.message]
    check("F15 spec/ 目录缺失 → P1", len(p1) >= 1 and not summary.passed)
    shutil.rmtree(root, ignore_errors=True)

    # F16: skip 语义（作用域无交集）
    check("F16 skip 语义（非作用域文件）",
          in_scope(["other/notes.txt"]) is False and in_scope([]) is True
          and in_scope(["CODE_WIKI.md"]) is True
          and in_scope(["docs\\M7_EVIDENCE_LOG.md"]) is True)

    # F17: 确定性（双跑输出逐字节一致）
    root = _build_mini_repo("")
    out1 = _format_results(_verify(root)[0])
    out2 = _format_results(_verify(root)[0])
    check("F17 确定性（双跑逐字节一致）", out1 == out2)
    shutil.rmtree(root, ignore_errors=True)

    # F18: I-4 数据驱动（stats 块改模式 → 同仓不同命中）
    root = _build_mini_repo("")
    before = _verify(root)[0]
    wiki_bad = MINI_WIKI_BODY.replace("双 hook", "两 hook")  # PT-D 命中「两」=2=真值过
    with open(os.path.join(root, "CODE_WIKI.md"), "w", encoding="utf-8") as f:
        f.write(wiki_bad.replace("{stats}", _mini_stats_json()))
    after = _verify(root)[0]
    check("F18 两 hook 变体等值通过（模式数据驱动）", before.passed and after.passed)
    shutil.rmtree(root, ignore_errors=True)

    # F19: 版本头叙事数字在扫描面（I-7 修正轮产出）
    wiki = MINI_WIKI_BODY.replace(
        "当前态：样本①-③，形态 II 9 处",
        "> 版本头叙事：本轮修完即绿，样本①-⑤，形态 II 12 处——修正轮产物\n\n当前态：样本①-③，形态 II 9 处")
    root = _build_mini_repo("", wiki_body=wiki)
    summary, _ = _verify(root)
    p2 = [r for r in summary.results if r.severity == "P2"
          and ("PT-A" in r.message and "12" in r.message
               or "PT-B" in r.message and "5" in r.message)]
    check("F19 版本头叙事数字在扫描面 → P2", len(p2) >= 2 and not summary.passed)
    shutil.rmtree(root, ignore_errors=True)

    # F20: doc_registry 行定位 = 链接形态（叙事行含 label 子串不误命中）
    wiki = MINI_WIKI_BODY.replace(
        "| [docs/FRAME.md](./docs/FRAME.md) | 框架 v1.0 |",
        "| [docs/dev-log/](./docs/dev-log/) | DEV-001（框架）叙事提及 |\n"
        "| [docs/FRAME.md](./docs/FRAME.md) | 框架 v1.0 |")
    root = _build_mini_repo("", wiki_body=wiki)
    summary, _ = _verify(root)
    wrong = [r for r in summary.results
             if r.severity == "P2" and ("无版本号 token" in r.message or "无对应行" in r.message)]
    check("F20 doc_registry 链接形态定位（叙事子串不误命中）",
          len(wrong) == 0 and summary.passed)
    shutil.rmtree(root, ignore_errors=True)

    # F21: drift-gate 缺口三元组捕获（rs-decl 失配 → gap 非空 + 意图/证据/缺口）
    bad = json.loads(_mini_stats_json(pattern_lib_version=2))
    bad["declared"]["spec_feature_dirs"] = 9
    root = _build_mini_repo("", stats_json=json.dumps(bad, ensure_ascii=False))
    summary, _ = _verify(root)
    gapped = [r for r in summary.results
              if r.gap and "意图(声明) spec_feature_dirs=9" in r.gap
              and "证据(重数) 2" in r.gap and "过声明" in r.gap]
    check("F21 drift-gate 缺口三元组（意图→证据→缺口）", len(gapped) == 1 and not summary.passed)
    shutil.rmtree(root, ignore_errors=True)

    # F22: _gap_report 输出（version 2 激活 → 含 [gap-report] 块 + 载体分布）
    bad = json.loads(_mini_stats_json(pattern_lib_version=2))
    bad["declared"]["spec_feature_dirs"] = 9
    root = _build_mini_repo("", stats_json=json.dumps(bad, ensure_ascii=False))
    summary, spec = _verify(root)
    report = _gap_report(summary.results) if spec and spec.pattern_lib_version >= 2 else ""
    ok22 = ("[gap-report]" in report and "rs-decl" in report
            and "CODE_WIKI.md×1" in report and "过声明" in report)
    check("F22 gap-report 块（version 2 激活）", ok22)
    shutil.rmtree(root, ignore_errors=True)

    # F23: version 1 不激活 gap-report（缺口在场但输出块空）
    bad = json.loads(_mini_stats_json(pattern_lib_version=1))
    bad["declared"]["spec_feature_dirs"] = 9
    root = _build_mini_repo("", stats_json=json.dumps(bad, ensure_ascii=False))
    summary, spec = _verify(root)
    gapped = [r for r in summary.results if r.gap]
    report = _gap_report(summary.results) if spec and spec.pattern_lib_version >= 2 else ""
    check("F23 version 1 缺口在场但 gap-report 不激活",
          len(gapped) == 1 and report == "")
    shutil.rmtree(root, ignore_errors=True)

    # F24: stats 块 pattern_lib_version 2 解析（drift-gate 激活登记读通）
    wiki_v2 = MINI_WIKI_BODY.replace("{stats}", _mini_stats_json(pattern_lib_version=2))
    spec_v2 = parse_stats_block(wiki_v2)[0]
    check("F24 pattern_lib_version=2 解析（drift-gate 激活）",
          spec_v2 is not None and spec_v2.pattern_lib_version == 2)

    # I-1 只读：迷你仓双跑文件字节不变
    root = _build_mini_repo("")
    before_bytes = {p: open(os.path.join(root, p), "rb").read()
                    for p in ["CODE_WIKI.md", "README.md", "docs/M7_EVIDENCE_LOG.md"]}
    _verify(root)
    _verify(root)
    after_bytes = {p: open(os.path.join(root, p), "rb").read()
                   for p in ["CODE_WIKI.md", "README.md", "docs/M7_EVIDENCE_LOG.md"]}
    check("I-1 全模式只读（双跑字节不变）", before_bytes == after_bytes)
    shutil.rmtree(root, ignore_errors=True)

    print(f"selftest: {passed}/{total} PASS")
    if failures:
        print("FAILED:", "; ".join(failures))
        return 1
    return 0


# ---------------------------------------------------------------- 输出与 CLI

def _gap_report(results: list) -> str:
    """drift-gate 缺口报告（pattern_lib_version ≥2 激活；DESIGN §6.1 意图→证据→缺口）。

    从已收集 CheckResult 的 gap 字段派生「意图 vs 证据 vs 缺口」三元组摘要 + 载体分布。
    无结构化缺口 → 返回空串（不输出块）。
    """
    gaps = [r for r in results if r.gap]
    if not gaps:
        return ""
    lines = [f"[gap-report] drift-gate 激活（意图→证据→缺口，{len(gaps)} 条）"]
    for r in gaps:
        loc = f"{r.file}" + (f":L{r.line}" if r.line else "")
        lines.append(f"  - [{r.severity}] {r.check_id} {loc}: {r.gap}")
    by_file: dict[str, int] = {}
    for r in gaps:
        by_file[r.file] = by_file.get(r.file, 0) + 1
    dist = " ".join(f"{k}×{v}" for k, v in sorted(by_file.items()))
    lines.append(f"  缺口分布: {dist}")
    return "\n".join(lines)


def _format_results(summary: Summary) -> str:
    lines = []
    for r in summary.results:
        if not r.severity:
            continue
        loc = f"{r.file}" + (f":L{r.line}" if r.line else "")
        lines.append(f"[{r.severity}] {loc} {r.message}")
    return "\n".join(lines)


def in_scope(files: list[str]) -> bool:
    """staged 文件 ∩ 对账作用域判定；空列表（本地直跑）= True 全量。"""
    if not files:
        return True
    for f in files:
        norm = f.replace("\\", "/")
        if SCOPE_RE.match(norm):
            return True
    return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="repo_stats 视图层机械枚举校验器（对账制，只读）")
    parser.add_argument("--selftest", action="store_true", help="内嵌自测（20 fixture）")
    parser.add_argument("files", nargs="*", help="pre-commit 传入的 staged 文件")
    args = parser.parse_args(argv)

    if args.selftest:
        return run_selftest()

    try:
        if args.files and not in_scope(args.files):
            print("[skip] 非对账作用域目标（视图载体集 ∪ 真值源集无交集）")
            return 0

        wiki_text = _read(os.path.join(ROOT, CODE_WIKI_PATH))
        if wiki_text is None:
            print(f"[P1] {CODE_WIKI_PATH} 不可读")
            return 1
        spec, r0 = parse_stats_block(wiki_text)
        results = list(r0)
        if spec is not None:
            truth, r1 = build_truth_set(spec, ROOT)
            results.extend(r1)
            results.extend(reconcile(spec, truth, ROOT))
        summary = Summary(results)
        print(_format_results(summary))
        if spec is not None and spec.pattern_lib_version >= 2:
            gr = _gap_report(results)
            if gr:
                print(gr)
        n_p1 = sum(1 for r in summary.violations if r.severity == "P1")
        n_p2 = sum(1 for r in summary.violations if r.severity == "P2")
        n_p3 = len(summary.p3s)
        if summary.passed:
            print(f"repo_stats 视图层对账通过：0 违规（P3 提示 {n_p3}）")
            return 0
        print(f"repo_stats 视图层对账失败：{len(summary.violations)} 违规（P1={n_p1} P2={n_p2}，P3 提示 {n_p3}）")
        return 1
    except Exception as e:  # noqa: BLE001 —— 顶层兜底（退出码 2，同 dc_validator/m7_stats）
        print(f"[tool-error] {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
