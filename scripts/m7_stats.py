#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M7 证据账本统计校验器（hits 机读块 + 表算术 + 跨表对账）——R7 同构。

权威源：spec/m7-hits-block/M7_HITS_DESIGN.md §4（hits 契约与校验规则集）
       + docs/M7_EVIDENCE_LOG.md（表结构单一真值源，I-4）。
表结构常量逐字符对应 M7 现行表头——M7 表变更须先改 M7（+DESIGN）再改此常量，同 commit。

不变式（DESIGN §8）：I-1 默认只读（--write 显式且写守卫）/ I-2 确定性（无时间态字段）
/ I-3 零新规则 / I-4 单一真值源（表头名序校验）/ I-5 异构于生成端（纯机械解析）
/ I-6 声明 = 重数（R7 同构）。
退出码：0 全部通过 / 1 发现违规（或 --write 拒绝写入）/ 2 工具自身错误。

用法：
  python scripts/m7_stats.py                              # 校验 docs/M7_EVIDENCE_LOG.md
  python scripts/m7_stats.py --write                      # 校验先行，重数值重写 hits 块
  python scripts/m7_stats.py --write --seed-pre-ledger 6  # hits 块缺失时的 bootstrap
  python scripts/m7_stats.py --selftest                   # 内嵌自测（16 fixture）
  pre-commit：传入 staged 文件名，非 M7 账本目标即 skip
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sys
from dataclasses import dataclass

# --- 仓库根（脚本位于 <root>/scripts/，与 cwd 无关，I-2） ---
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
M7_PATH = "docs/M7_EVIDENCE_LOG.md"

# --- 表结构契约（I-4 单一真值源 = M7 现行表头） ---
SAMPLE_COLS = ("#", "日期", "载体", "审查配置", "发现", "形态II复发", "来源")
BUCKET_COLS = ("载体 \\ 字段类型", "版本号", "章节号", "数值常量", "行号",
               "计数", "转述引文", "映射闭合", "小计")
FIELD_KEYS = (("版本号", "version"), ("章节号", "section"), ("数值常量", "constant"),
              ("行号", "line"), ("计数", "count"), ("转述引文", "quote"),
              ("映射闭合", "mapping"))
HITS_TOP_KEYS = ("samples", "form2_by_field", "form2_total", "form2_pre_ledger",
                 "form2_from_samples", "findings")
FINDINGS_KEYS = ("p1", "p2", "p3", "unlabeled", "cells_nonstandard")

RE_S1 = re.compile(r"^##\s*1[\.、]?\s*样本登记表", re.M)
RE_S2 = re.compile(r"^##\s*2[\.、]?\s*形态\s*II\s*复发分桶", re.M)
RE_NEXT_SECTION = re.compile(r"^##\s")
RE_S5 = re.compile(r"^##\s*5")
RE_SEP_CELL = re.compile(r"^:?-{3,}:?$")
RE_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
RE_INT = re.compile(r"^\d+$")
RE_FORM2_LEAD = re.compile(r"^\s*(\d+)")
RE_P_TOKEN = re.compile(r"(\d+)\s*P([123])")
RE_LEAD_IS_P = re.compile(r"^\s*(\d+)(?=\s*P[123])")

S5_TITLE = "## 5. 机读统计块（hits）"
S5_INTRO = ("> 统计唯一声明处（R7 同构：声明 = 机械重数）。重生成：`python scripts/m7_stats.py --write`"
            "（校验先行 + 写守卫——失衡账本不可写入）；提交瞬间由 pre-commit hook `m7-stats` 自动校验。"
            "字段语义：[M7_HITS_DESIGN §4](../spec/m7-hits-block/M7_HITS_DESIGN.md)。")


@dataclass(frozen=True)
class CheckResult:
    check_id: str      # "m7-sample" | "m7-bucket" | "m7-xtable" | "m7-hits"
    file: str
    severity: str      # "P1" | "P2" | "P3" | ""（空 = skip）
    message: str
    line: int | None = None


class Summary:
    """违规 = P1/P2（阻断）；P3 = 历史非整齐形态的如实提示，非阻断（DESIGN §4.3）。"""

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
class SampleRow:
    num: int
    date: str
    findings: str
    form2_count: int


@dataclass(frozen=True)
class BucketRow:
    label: str
    vals: tuple            # 7 字段格（— 记 0）
    sub: int               # 小计
    line: int


@dataclass(frozen=True)
class Stats:
    samples: int
    by_field: tuple        # 7 int，FIELD_KEYS 序
    form2_total: int
    form2_from_samples: int
    findings: tuple        # (p1, p2, p3, unlabeled, cells_nonstandard)


# ---------------------------------------------------------------- 解析基元

def _read(full):
    with open(full, encoding="utf-8", newline="", errors="replace") as fh:
        return fh.read()


def split_cells(line):
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in s.split("|")]


def extract_section(text, header_re):
    """返回 [(全局行号, 行文本), ...]——节标题之后到下一 ## 节之前；节缺失返回 None。"""
    lines = text.splitlines()
    start = None
    for i, ln in enumerate(lines):
        if header_re.match(ln):
            start = i
            break
    if start is None:
        return None
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if RE_NEXT_SECTION.match(lines[j]):
            end = j
            break
    return [(start + 1 + k, ln) for k, ln in enumerate(lines[start + 1:end])]


def _is_sep(cells):
    non_empty = [c for c in cells if c]
    return bool(non_empty) and all(RE_SEP_CELL.match(c) for c in non_empty)


def _valid_date(s):
    try:
        datetime.date(int(s[:4]), int(s[5:7]), int(s[8:10]))
        return True
    except ValueError:
        return False


def _cell_val(c):
    c = c.strip().strip("*").strip()
    if RE_INT.match(c):
        return int(c)
    if c == "—":
        return 0
    return None


def parse_findings(cell):
    """发现列 → (ptok{1,2,3}, p_total, lead|None, nonstandard)。

    lead 语义：前导总数（如 `10（2P1+…）` 的 10）；前导整数实为 P 标记
    （如 `2P2+6P3` / `3 P3（…）`）时无前导总数。非标准 = 无前导总数且无 P 标记
    （样本③ 形态，P3 非阻断，计入 cells_nonstandard）。
    """
    ptok = {"1": 0, "2": 0, "3": 0}
    for m in RE_P_TOKEN.finditer(cell):
        ptok[m.group(2)] += int(m.group(1))
    p_total = ptok["1"] + ptok["2"] + ptok["3"]
    lead = None
    if not RE_LEAD_IS_P.match(cell):
        m = re.match(r"\s*(\d+)", cell)
        if m:
            lead = int(m.group(1))
    nonstandard = lead is None and p_total == 0
    return ptok, p_total, lead, nonstandard


# ---------------------------------------------------------------- MH2 样本表

def parse_sample_table(file, text):
    """返回 (list[SampleRow] | None, list[CheckResult])。None = 节缺失。"""
    sec = extract_section(text, RE_S1)
    if sec is None:
        return None, [CheckResult("m7-sample", file, "P1", "§1 样本登记表节缺失")]
    pipe_rows = [(ln, split_cells(l)) for ln, l in sec if l.lstrip().startswith("|")]
    if not pipe_rows:
        return [], [CheckResult("m7-sample", file, "P1", "§1 样本登记表无表行")]
    results = []
    hln, hcells = pipe_rows[0]
    if tuple(hcells) != SAMPLE_COLS:
        results.append(CheckResult("m7-sample", file, "P1",
                                   "§1 表头名序不符契约: %r（期望 %r）" % (hcells, list(SAMPLE_COLS)), hln))
    rows = []
    for ln, cells in pipe_rows[1:]:
        if _is_sep(cells):
            continue
        if len(cells) != 7:
            results.append(CheckResult("m7-sample", file, "P1",
                                       "样本行列数 %d ≠ 7" % len(cells), ln))
            continue
        if not RE_INT.match(cells[0]):
            results.append(CheckResult("m7-sample", file, "P1",
                                       "样本号非整数: %r" % cells[0], ln))
            continue
        if not RE_DATE.match(cells[1]) or not _valid_date(cells[1]):
            results.append(CheckResult("m7-sample", file, "P2",
                                       "日期非法: %r" % cells[1], ln))
        if not cells[4]:
            results.append(CheckResult("m7-sample", file, "P1", "发现列为空（行结构损坏）", ln))
            continue
        m = RE_FORM2_LEAD.match(cells[5])
        if not m:
            results.append(CheckResult("m7-sample", file, "P1",
                                       "形态II复发列无前导整数: %r" % cells[5][:30], ln))
            continue
        rows.append(SampleRow(int(cells[0]), cells[1], cells[4], int(m.group(1))))
    # 发现列逐行 P 抽取校验（统计聚合在 compute_stats）
    for r in rows:
        _ptok, p_total, lead, nonstd = parse_findings(r.findings)
        if lead is not None and p_total > lead:
            results.append(CheckResult("m7-sample", file, "P1",
                                       "发现列 P 标记和 %d > 前导总数 %d" % (p_total, lead)))
        if nonstd:
            results.append(CheckResult("m7-sample", file, "P3",
                                       "发现列非标准形态（无前导总数且无 P 标记），计入 cells_nonstandard"))
    nums = [r.num for r in rows]
    if nums != list(range(1, len(nums) + 1)):
        results.append(CheckResult("m7-sample", file, "P1",
                                   "样本编号非 1..N 连续: %s" % nums))
    return rows, results


# ---------------------------------------------------------------- MH3 分桶表

def parse_bucket_table(file, text):
    """返回 ((rows, totals | None), list[CheckResult])。totals=(vals7, 小计, 行号)。"""
    sec = extract_section(text, RE_S2)
    if sec is None:
        return (None, None), [CheckResult("m7-bucket", file, "P1", "§2 形态II复发分桶节缺失")]
    pipe_rows = [(ln, split_cells(l)) for ln, l in sec if l.lstrip().startswith("|")]
    if not pipe_rows:
        return ([], None), [CheckResult("m7-bucket", file, "P1", "§2 分桶表无表行")]
    results = []
    hln, hcells = pipe_rows[0]
    if tuple(hcells) != BUCKET_COLS:
        results.append(CheckResult("m7-bucket", file, "P1",
                                   "§2 表头名序不符契约: %r（期望 %r）" % (hcells, list(BUCKET_COLS)), hln))
    data, totals_rows = [], []
    for ln, cells in pipe_rows[1:]:
        if _is_sep(cells):
            continue
        if cells and cells[0].strip("*").strip() == "合计":
            totals_rows.append((ln, cells))
        else:
            data.append((ln, cells))
    if len(totals_rows) != 1:
        results.append(CheckResult("m7-bucket", file, "P1", "合计行数 %d ≠ 1" % len(totals_rows)))
    rows = []
    for ln, cells in data:
        if len(cells) != 9:
            results.append(CheckResult("m7-bucket", file, "P1",
                                       "分桶行列数 %d ≠ 9" % len(cells), ln))
            continue
        vals = [_cell_val(c) for c in cells[1:8]]
        sub = _cell_val(cells[8])
        if None in vals or sub is None:
            results.append(CheckResult("m7-bucket", file, "P1",
                                       "分桶行单元格非 {整数, —}: %r" % (cells[1:],), ln))
            continue
        if sum(vals) != sub:
            results.append(CheckResult("m7-bucket", file, "P1",
                                       "行算术: 小计 %d ≠ 行和 %d（%s）" % (sub, sum(vals), cells[0][:20]), ln))
        rows.append(BucketRow(cells[0], tuple(vals), sub, ln))
    totals = None
    if len(totals_rows) == 1:
        tln, tcells = totals_rows[0]
        if len(tcells) != 9:
            results.append(CheckResult("m7-bucket", file, "P1", "合计行列数 %d ≠ 9" % len(tcells), tln))
        else:
            tvals = [_cell_val(c) for c in tcells[1:8]]
            tsub = _cell_val(tcells[8])
            if None in tvals or tsub is None:
                results.append(CheckResult("m7-bucket", file, "P1",
                                           "合计行单元格非 {整数, —}", tln))
            else:
                totals = (tuple(tvals), tsub, tln)
    if totals is not None:
        tvals, tsub, tln = totals
        for idx, (cname, _k) in enumerate(FIELD_KEYS):
            colsum = sum(r.vals[idx] for r in rows)
            if colsum != tvals[idx]:
                results.append(CheckResult("m7-bucket", file, "P1",
                                           "列算术: %s 合计 %d ≠ 列和 %d" % (cname, tvals[idx], colsum), tln))
        subsum = sum(r.sub for r in rows)
        if tsub != subsum:
            results.append(CheckResult("m7-bucket", file, "P1",
                                       "列算术: 合计小计 %d ≠ 数据行小计和 %d" % (tsub, subsum), tln))
        if sum(tvals) != tsub:
            results.append(CheckResult("m7-bucket", file, "P1",
                                       "行算术: 合计行小计 %d ≠ 自身行和 %d" % (tsub, sum(tvals)), tln))
    return (rows, totals), results


# ---------------------------------------------------------------- MH4 统计/对账

def compute_stats(srows, totals):
    p1 = p2 = p3 = unl = nonstd = 0
    for r in srows:
        ptok, p_total, lead, ns = parse_findings(r.findings)
        p1 += ptok["1"]
        p2 += ptok["2"]
        p3 += ptok["3"]
        if lead is not None:
            unl += max(0, lead - p_total)
        if ns:
            nonstd += 1
    tvals, tsub, _tln = totals
    return Stats(len(srows), tuple(tvals), tsub,
                 sum(r.form2_count for r in srows),
                 (p1, p2, p3, unl, nonstd))


def check_xtable(file, stats, pre_ledger):
    if pre_ledger is None or stats is None:
        return []
    if stats.form2_total != pre_ledger + stats.form2_from_samples:
        return [CheckResult("m7-xtable", file, "P1",
                            "跨表对账: 分桶合计 %d ≠ 基线 %d + 样本列和 %d"
                            % (stats.form2_total, pre_ledger, stats.form2_from_samples))]
    return []


def extract_hits_spans(text):
    """返回 [(开围栏行号0基, 闭围栏行号0基, 块内容), ...]；未闭合返回特殊标记。"""
    lines = text.splitlines()
    spans, unclosed = [], []
    i = 0
    while i < len(lines):
        if lines[i].strip() == "```hits":
            j = i + 1
            while j < len(lines) and lines[j].strip() != "```":
                j += 1
            if j >= len(lines):
                unclosed.append(i)
                i = j
            else:
                spans.append((i, j, "\n".join(lines[i + 1:j])))
                i = j + 1
        else:
            i += 1
    return spans, unclosed


def _is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def compare_hits(file, declared, stats):
    """hits 声明 vs 机械重数（form2_pre_ledger 为声明量，不参与比对，仅受 xtable 约束）。"""
    results = []
    extra = [k for k in declared if k not in HITS_TOP_KEYS]
    if extra:
        results.append(CheckResult("m7-hits", file, "P1", "hits 含契约外字段: %s" % extra))
    simple = (("samples", stats.samples),
              ("form2_total", stats.form2_total),
              ("form2_from_samples", stats.form2_from_samples))
    for k, actual in simple:
        if k not in declared:
            results.append(CheckResult("m7-hits", file, "P1", "hits 缺字段: %s" % k))
        elif declared[k] != actual:
            results.append(CheckResult("m7-hits", file, "P1",
                                       "hits %s 声明 %r 实为 %r" % (k, declared[k], actual)))
    if "form2_pre_ledger" not in declared:
        results.append(CheckResult("m7-hits", file, "P1", "hits 缺字段: form2_pre_ledger"))
    elif not _is_int(declared["form2_pre_ledger"]):
        results.append(CheckResult("m7-hits", file, "P1",
                                   "hits form2_pre_ledger 非整数: %r" % (declared["form2_pre_ledger"],)))
    d = declared.get("form2_by_field")
    if not isinstance(d, dict):
        results.append(CheckResult("m7-hits", file, "P1",
                                   "hits form2_by_field 非对象: %r" % (d,)))
    else:
        extra_f = [k for k in d if k not in dict(FIELD_KEYS).values()]
        if extra_f:
            results.append(CheckResult("m7-hits", file, "P1",
                                       "hits form2_by_field 含契约外键: %s" % extra_f))
        for idx, (_cn, key) in enumerate(FIELD_KEYS):
            if key not in d:
                results.append(CheckResult("m7-hits", file, "P1",
                                           "hits form2_by_field 缺键: %s" % key))
            elif d[key] != stats.by_field[idx]:
                results.append(CheckResult("m7-hits", file, "P1",
                                           "hits form2_by_field.%s 声明 %r 实为 %r"
                                           % (key, d[key], stats.by_field[idx])))
    f = declared.get("findings")
    if not isinstance(f, dict):
        results.append(CheckResult("m7-hits", file, "P1", "hits findings 非对象: %r" % (f,)))
    else:
        extra_k = [k for k in f if k not in FINDINGS_KEYS]
        if extra_k:
            results.append(CheckResult("m7-hits", file, "P1",
                                       "hits findings 含契约外键: %s" % extra_k))
        for idx, key in enumerate(FINDINGS_KEYS):
            if key not in f:
                results.append(CheckResult("m7-hits", file, "P1", "hits findings 缺键: %s" % key))
            elif f[key] != stats.findings[idx]:
                results.append(CheckResult("m7-hits", file, "P1",
                                           "hits findings.%s 声明 %r 实为 %r"
                                           % (key, f[key], stats.findings[idx])))
    return results


def serialize_hits(stats, pre_ledger):
    """确定性序列化（I-2/I-6）：字段序固定，无时间态。"""
    obj = {
        "samples": stats.samples,
        "form2_by_field": {key: stats.by_field[idx] for idx, (_cn, key) in enumerate(FIELD_KEYS)},
        "form2_total": stats.form2_total,
        "form2_pre_ledger": pre_ledger,
        "form2_from_samples": stats.form2_from_samples,
        "findings": dict(zip(FINDINGS_KEYS, stats.findings)),
    }
    return json.dumps(obj, ensure_ascii=False, indent=2)


def analyze(file, text):
    """全量校验。返回 (results, stats|None, declared|None, pre_ledger|None, spans)。"""
    results = []
    srows, r1 = parse_sample_table(file, text)
    results += r1
    (brows, totals), r2 = parse_bucket_table(file, text)
    results += r2
    spans, unclosed = extract_hits_spans(text)
    declared, pre_ledger = None, None
    for u in unclosed:
        results.append(CheckResult("m7-hits", file, "P1", "hits 围栏未闭合（L%d）" % (u + 1), u + 1))
    if len(spans) == 0 and not unclosed:
        results.append(CheckResult("m7-hits", file, "P1", "hits 块缺失"))
    elif len(spans) > 1:
        results.append(CheckResult("m7-hits", file, "P1", "hits 围栏块 %d 个 ≠ 1" % len(spans)))
    elif len(spans) == 1:
        try:
            declared = json.loads(spans[0][2])
        except ValueError as e:
            results.append(CheckResult("m7-hits", file, "P1", "hits JSON 不可解析: %s" % e))
            declared = None
        if declared is not None and not isinstance(declared, dict):
            results.append(CheckResult("m7-hits", file, "P1",
                                       "hits 块非 JSON 对象: %r" % (declared,)))
            declared = None
    stats = None
    if srows is not None and totals is not None:
        stats = compute_stats(srows, totals)
    if isinstance(declared, dict):
        v = declared.get("form2_pre_ledger")
        if _is_int(v):
            pre_ledger = v
        if stats is not None:
            results += compare_hits(file, declared, stats)
            results += check_xtable(file, stats, pre_ledger)
    return results, stats, declared, pre_ledger, spans


# ---------------------------------------------------------------- --write

def _detect_eol(text):
    return "\r\n" if "\r\n" in text else "\n"


def build_new_text(text, block_content, spans):
    """hits 块存在 → 围栏内替换；缺失 → 追加 §5（bootstrap）。返回新全文或 None（不可写）。"""
    eol = _detect_eol(text)
    trailing = eol if text.endswith(("\n", "\r\n")) else ""
    lines = text.splitlines()
    if spans:
        i, j, _ = spans[0]
        new_lines = lines[:i + 1] + block_content.split("\n") + lines[j:]
        return eol.join(new_lines) + trailing
    if any(RE_S5.match(ln) for ln in lines):
        return None  # 已有 §5 节却无 hits 围栏——非脚本可修复形态
    base = text + eol if text and not text.endswith(("\n", "\r\n")) else text
    sect = [S5_TITLE, "", S5_INTRO, "", "```hits"] + block_content.split("\n") + ["```"]
    return base + eol.join(sect) + eol


# ---------------------------------------------------------------- M1 CLI

def _looks_like_ledger(full):
    try:
        text = _read(full)
    except OSError:
        return False
    return bool(RE_S1.search(text) or RE_S2.search(text) or "```hits" in text)


def run_targets(targets, args):
    all_results = []
    for disp, full in targets:
        try:
            text = _read(full)
        except OSError as e:
            all_results.append(CheckResult("m7-hits", disp, "P2", "文件不可读: %s" % e))
            continue
        results, stats, declared, pre_ledger, spans = analyze(disp, text)
        if not args.write:
            all_results += results
            continue
        # 写守卫（DESIGN §3.4）：非 hits 类阻断 + hits 类不可修复形态 → 拒绝写入
        blocking = [r for r in results
                    if r.severity in ("P1", "P2") and r.check_id != "m7-hits"]
        unfixable = [r for r in results
                     if r.severity in ("P1", "P2") and r.check_id == "m7-hits"
                     and ("不可解析" in r.message or "≠ 1" in r.message
                          or "未闭合" in r.message or "非 JSON 对象" in r.message)]
        need_seed = not spans
        if stats is None or blocking or unfixable:
            all_results += results  # 违规如实聚合，exit 1
            continue
        if need_seed:
            if args.seed_pre_ledger is None:
                all_results += results
                all_results.append(CheckResult(
                    "m7-hits", disp, "P1",
                    "--write 需要 --seed-pre-ledger N（hits 块缺失，历史基线须人工声明）"))
                continue
            pre = args.seed_pre_ledger
        else:
            if pre_ledger is None:
                all_results += results  # pre_ledger 缺失/非整数已报 P1（m7-hits），不可写
                continue
            pre = pre_ledger
        xt = check_xtable(disp, stats, pre)
        if xt:
            all_results += results + xt
            continue
        new_text = build_new_text(text, serialize_hits(stats, pre), spans)
        if new_text is None:
            all_results += results
            all_results.append(CheckResult(
                "m7-hits", disp, "P1", "存在 §5 节却无 hits 围栏——须人工修复后重试"))
            continue
        # 写后自检（内存态）：落盘前必须全绿，否则视为工具自身错误
        recheck, _s2_, _d2_, _p2_, _sp2_ = analyze(disp, new_text)
        if any(r.severity in ("P1", "P2") for r in recheck):
            print("[tool-error] 写后自检失败（序列化与重数不一致），未落盘")
            return all_results, 2
        with open(full, "w", encoding="utf-8", newline="") as fh:
            fh.write(new_text)
        print("hits 块已重生成: %s（samples=%d, form2_total=%d, pre_ledger=%d, from_samples=%d）"
              % (disp, stats.samples, stats.form2_total, pre, stats.form2_from_samples))
        # 写成功 → 聚合写后状态（写前的 hits 失配声明已被修复，不再计入）
        all_results += recheck
    return all_results, None


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    ap = argparse.ArgumentParser(prog="m7_stats",
                                 description="M7 证据账本统计校验器（hits 机读块 + 表算术 + 跨表对账）")
    ap.add_argument("--write", action="store_true",
                    help="校验先行，以机械重数值重写 hits 块（写守卫）")
    ap.add_argument("--seed-pre-ledger", type=int, default=None, metavar="N",
                    help="hits 块缺失时 bootstrap 所需历史基线（= 先于账本的分桶小计合计）")
    ap.add_argument("--selftest", action="store_true", help="内嵌自测（16 fixture）")
    ap.add_argument("files", nargs="*",
                    help="目标文件（缺省 = docs/M7_EVIDENCE_LOG.md；pre-commit 传入 staged 列表）")
    args = ap.parse_args(argv)
    if args.selftest:
        return run_selftest()

    try:
        files = args.files if args.files else [M7_PATH]
        targets = []
        for f in files:
            norm = f.replace("\\", "/")
            full = f if os.path.isabs(f) else os.path.normpath(os.path.join(ROOT, f))
            if norm == M7_PATH or _looks_like_ledger(full):
                targets.append((f, full))
        if args.files and not targets:
            print("[skip] staged 文件不含 M7 账本目标")
            return 0
        results, forced_exit = run_targets(targets, args)
    except Exception as e:  # 工具自身错误 ≠ 校验通过
        sys.stderr.write("[tool-error] %s: %s\n" % (type(e).__name__, e))
        return 2
    if forced_exit:
        return forced_exit

    summary = Summary(results)
    for r in summary.results:
        tag = "[%s]" % r.severity if r.severity else "[skip]"
        loc = " (L%d)" % r.line if r.line else ""
        print("%s %s: %s%s" % (tag, r.file, r.message, loc))
    if summary.passed:
        note = "（P3 提示 %d）" % len(summary.p3s) if summary.p3s else ""
        print("M7 统计校验通过：%d 结果，0 违规%s" % (len(summary.results), note))
        return 0
    print("M7 统计校验失败：%d 违规（P1=%d P2=%d，P3 提示 %d）" % (
        len(summary.violations),
        sum(1 for r in summary.violations if r.severity == "P1"),
        sum(1 for r in summary.violations if r.severity == "P2"),
        len(summary.p3s)))
    return 1


# ---------------------------------------------------------------- MH5 selftest

MINI = """# M7 测试账本

## 1. 样本登记表

| # | 日期 | 载体 | 审查配置 | 发现 | 形态II复发 | 来源 |
|---|------|------|---------|------|-----------|------|
| 1 | 2026-08-16 | 载体甲 | 同基座自查 | 10（2P1+5P2+3P3） | 2（计数/行号） | PLAN §6 |
| 2 | 2026-08-17 | 载体乙 | 异构双盲 | 2P2+6P3 | 0 | AUDIT §3 |

## 2. 形态 II 复发分桶（载体 × 字段类型）

| 载体 \\ 字段类型 | 版本号 | 章节号 | 数值常量 | 行号 | 计数 | 转述引文 | 映射闭合 | 小计 |
|---|---|---|---|---|---|---|---|---|
| 载体甲（测试） | — | — | — | 1 | 1 | — | — | 2 |
| 载体乙（测试） | — | — | — | — | — | — | — | 0 |
| **合计** | 0 | 0 | 0 | 1 | 1 | 0 | 0 | **2** |

## 3. 命中率 baseline

| 来源 | review 修正数 | 锚点 |
|------|-------------|------|
| Cpp_Hub Phase 5 | 14 处 | AUDIT L462 |
"""

HITS_VALID = """```hits
{
  "samples": 2,
  "form2_by_field": {
    "version": 0,
    "section": 0,
    "constant": 0,
    "line": 1,
    "count": 1,
    "quote": 0,
    "mapping": 0
  },
  "form2_total": 2,
  "form2_pre_ledger": 0,
  "form2_from_samples": 2,
  "findings": {
    "p1": 2,
    "p2": 7,
    "p3": 9,
    "unlabeled": 0,
    "cells_nonstandard": 0
  }
}
```"""


def run_selftest():
    """十六 fixture（IMPLEMENTATION §8.1 F1-F16），tempfile 构造于系统临时目录。"""
    import contextlib
    import io
    import shutil
    import tempfile

    tmp = tempfile.mkdtemp(prefix="m7stats_selftest_")
    fails = []
    total = [0]  # 机械计数（R7 同构：计数由 expect 调用自增，不手填）

    def expect(cond, msg):
        total[0] += 1
        print("  %s %s" % ("PASS" if cond else "FAIL", msg))
        if not cond:
            fails.append(msg)

    def w(name, content):
        p = os.path.join(tmp, name)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(content)
        return p

    try:
        # F1 合规迷你账本 + skip 语义
        f1 = w("f1.md", MINI + "\n" + HITS_VALID + "\n")
        res, stats, _decl, _pre, _sp = analyze("f1.md", _read(f1))
        expect(not any(r.severity in ("P1", "P2") for r in res), "F1 合规账本零违规")
        expect(stats is not None and stats.samples == 2, "F1 samples=2")
        expect(stats is not None and stats.by_field == (0, 0, 0, 1, 1, 0, 0), "F1 by_field 行号1/计数1")
        expect(stats is not None and stats.form2_total == 2, "F1 form2_total=2")
        expect(stats is not None and stats.form2_from_samples == 2, "F1 from_samples=2")
        expect(stats is not None and stats.findings == (2, 7, 9, 0, 0), "F1 findings=(2,7,9,0,0)")
        expect(main([f1]) == 0, "F1 verify exit 0")
        plain = w("plain.md", "# plain doc\n")
        expect(main([plain]) == 0, "F1 skip 非 M7 目标")

        # F2 编号断档
        f2 = w("f2.md", MINI.replace("| 2 | 2026-08-17", "| 3 | 2026-08-17") + "\n" + HITS_VALID + "\n")
        res, _, _, _, _ = analyze("f2.md", _read(f2))
        expect(any(r.severity == "P1" and "连续" in r.message for r in res), "F2 编号断档报 P1")

        # F3 列数 6
        f3 = w("f3.md", MINI.replace(
            "| 2 | 2026-08-17 | 载体乙 | 异构双盲 | 2P2+6P3 | 0 | AUDIT §3 |",
            "| 2 | 2026-08-17 | 载体乙 | 异构双盲 | 2P2+6P3 | AUDIT §3 |") + "\n" + HITS_VALID + "\n")
        res, _, _, _, _ = analyze("f3.md", _read(f3))
        expect(any(r.severity == "P1" and "列数" in r.message for r in res), "F3 列数 6 报 P1")

        # F4 日期非法（P2）
        f4 = w("f4.md", MINI.replace("2026-08-17", "2026-13-01") + "\n" + HITS_VALID + "\n")
        res, _, _, _, _ = analyze("f4.md", _read(f4))
        expect(any(r.severity == "P2" and "日期" in r.message for r in res), "F4 日期非法报 P2")
        expect(main([f4]) == 1, "F4 exit 1（P2 阻断）")

        # F5 形态II复发无前导整数
        f5 = w("f5.md", MINI.replace("| 0 | AUDIT §3 |", "| （无前导） | AUDIT §3 |")
               + "\n" + HITS_VALID + "\n")
        res, _, _, _, _ = analyze("f5.md", _read(f5))
        expect(any(r.severity == "P1" and "前导整数" in r.message for r in res), "F5 前导缺失报 P1")

        # F6 行算术
        f6 = w("f6.md", MINI.replace("| 载体甲（测试） | — | — | — | 1 | 1 | — | — | 2 |",
                                     "| 载体甲（测试） | — | — | — | 1 | 1 | — | — | 3 |")
               + "\n" + HITS_VALID + "\n")
        res, _, _, _, _ = analyze("f6.md", _read(f6))
        expect(any(r.severity == "P1" and "行算术: 小计" in r.message for r in res), "F6 行算术报 P1")

        # F7 列算术
        f7 = w("f7.md", MINI.replace("| **合计** | 0 | 0 | 0 | 1 | 1 | 0 | 0 | **2** |",
                                     "| **合计** | 0 | 0 | 0 | 2 | 1 | 0 | 0 | **2** |")
               + "\n" + HITS_VALID + "\n")
        res, _, _, _, _ = analyze("f7.md", _read(f7))
        expect(any(r.severity == "P1" and "列算术" in r.message for r in res), "F7 列算术报 P1")

        # F8 跨表对账失衡（pre_ledger 声明 5）
        f8 = w("f8.md", MINI + "\n" +
               HITS_VALID.replace('"form2_pre_ledger": 0', '"form2_pre_ledger": 5') + "\n")
        res, _, _, _, _ = analyze("f8.md", _read(f8))
        expect(any(r.severity == "P1" and "跨表对账" in r.message for r in res), "F8 跨表对账报 P1")

        # F9 hits 声明失配 → --write 修复闭环
        f9 = w("f9.md", MINI + "\n" +
               HITS_VALID.replace('"samples": 2', '"samples": 3') + "\n")
        res, _, _, _, _ = analyze("f9.md", _read(f9))
        expect(any(r.severity == "P1" and "samples 声明 3 实为 2" in r.message for r in res),
               "F9 声明失配报 P1（declared/actual）")
        expect(main([f9]) == 1, "F9 verify exit 1")
        expect(main([f9, "--write"]) == 0, "F9 --write 修复 exit 0")
        expect(main([f9]) == 0, "F9 修复后 verify exit 0")
        expect('"samples": 2' in _read(f9), "F9 重写后 samples=2")

        # F10 bootstrap 全路径
        f10 = w("f10.md", MINI)
        expect(main([f10]) == 1, "F10 缺块 verify exit 1")
        before = open(f10, "rb").read()
        expect(main([f10, "--write"]) == 1, "F10 无 seed 拒绝写入 exit 1")
        expect(open(f10, "rb").read() == before, "F10 拒绝时文件字节不变")
        expect(main([f10, "--write", "--seed-pre-ledger", "0"]) == 0, "F10 seed 落盘 exit 0")
        expect("```hits" in _read(f10) and "## 5. 机读统计块" in _read(f10), "F10 §5 + 围栏块追加")
        expect(main([f10]) == 0, "F10 bootstrap 后 verify exit 0")

        # F11 P 抽取五形态（函数级）
        ptok, pt, lead, ns = parse_findings("10（2P1+5P2+3P3）")
        expect(lead == 10 and pt == 10 and not ns, "F11a 总数齐（lead=10, sum=10）")
        ptok, pt, lead, ns = parse_findings("4（1P1 计数漏计 + 2P2 断链 + 1 工具自身计数缺陷）")
        expect(lead == 4 and pt == 3 and not ns, "F11b unlabeled（lead=4, P和=3）")
        ptok, pt, lead, ns = parse_findings("R2 拦截 1/4；双盲 5/5 TRUE")
        expect(lead is None and pt == 0 and ns, "F11c 非标准（无 lead 无 P）")
        ptok, pt, lead, ns = parse_findings("2P2+6P3")
        expect(lead is None and ptok["2"] == 2 and ptok["3"] == 6, "F11d 无总数有 P")
        ptok, pt, lead, ns = parse_findings("3 P1（x）")
        expect(lead is None and ptok["1"] == 3, "F11e 前导实为 P 标记")
        ptok, pt, lead, ns = parse_findings("2（3P2）")
        expect(lead == 2 and pt == 3, "F11f P 和超总数（违规由行级校验报）")

        # F12 写守卫
        f12 = w("f12.md", MINI.replace("| 载体甲（测试） | — | — | — | 1 | 1 | — | — | 2 |",
                                       "| 载体甲（测试） | — | — | — | 1 | 1 | — | — | 5 |")
                + "\n" + HITS_VALID.replace('"samples": 2', '"samples": 9') + "\n")
        before = open(f12, "rb").read()
        expect(main([f12, "--write"]) == 1, "F12 存在阻断违规时 --write exit 1")
        expect(open(f12, "rb").read() == before, "F12 写守卫：文件字节不变")

        # F13 确定性
        f13 = w("f13.md", MINI + "\n" +
                HITS_VALID.replace('"form2_total": 2', '"form2_total": 8') + "\n")
        expect(main([f13, "--write"]) == 0, "F13 第一次 --write")
        b1 = open(f13, "rb").read()
        expect(main([f13, "--write"]) == 0, "F13 第二次 --write")
        b2 = open(f13, "rb").read()
        expect(b1 == b2, "F13 双跑产物逐字节一致")

        # F14 P3 非阻断
        f14 = w("f14.md", MINI.replace(
            "| 2 | 2026-08-17 | 载体乙 | 异构双盲 | 2P2+6P3 | 0 | AUDIT §3 |",
            "| 2 | 2026-08-17 | 载体乙 | 异构双盲 | R2 拦截 1/4；双盲 5/5 TRUE | 0 | AUDIT §3 |")
            + "\n" + HITS_VALID.replace('"p2": 7', '"p2": 5').replace('"p3": 9', '"p3": 3')
            .replace('"cells_nonstandard": 0', '"cells_nonstandard": 1') + "\n")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = main([f14])
        expect(code == 0, "F14 非标准单元格不阻断（exit 0）")
        expect("[P3]" in buf.getvalue(), "F14 [P3] 行打印可见")

        # F15 DR-B 发现列空值 → P1（行结构损坏）
        f15 = w("f15.md", MINI.replace("| 异构双盲 | 2P2+6P3 |", "| 异构双盲 |  |")
                + "\n" + HITS_VALID + "\n")
        res, _, _, _, _ = analyze("f15.md", _read(f15))
        expect(any(r.severity == "P1" and "发现列为空" in r.message for r in res),
               "F15 发现列空值报 P1")

        # F16 DR-C §5 节无 hits 围栏 → --write 拒绝（防追加第二个 §5）
        f16 = w("f16.md", MINI + "\n## 5. 机读统计块（hits）\n\n（围栏块被误删，须人工修复）\n")
        before16 = open(f16, "rb").read()
        buf16 = io.StringIO()
        with contextlib.redirect_stdout(buf16):
            code16 = main([f16, "--write", "--seed-pre-ledger", "0"])
        expect(code16 == 1, "F16 §5 无围栏 --write 拒绝 exit 1")
        expect("存在 §5 节却无 hits 围栏" in buf16.getvalue(), "F16 报人工修复提示")
        expect(open(f16, "rb").read() == before16, "F16 拒绝写入文件字节不变")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    if fails:
        print("selftest: %d/%d FAILED" % (len(fails), total[0]))
        return 1
    print("selftest: %d/%d PASS" % (total[0], total[0]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
