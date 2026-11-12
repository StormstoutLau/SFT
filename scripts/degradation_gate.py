#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""降级传播检查器（degradation gate）—— 本仓第六次复发后新增的门禁

为什么需要（真值源）：`docs/reviews/p010-pipeline.adjudication.md` 成立 1 记录——
「声明了降级却当结论用」这一形态在本仓**六次复发**（P-005 的 B9、P-006 的 §5.1 容量、
P-009 的三处容许带、P-010 的 Studio 主结论……）。每份文档都写了「本档要防这条」，
每次都犯 ⇒ **缺的不是自觉，是机械检查**。

判据（一句话）：同一文档内，某标识符（B9 / A-1 / L3 / U1 …）在**降级语境**里被标记为
未验证/未取证/E4/E5，却在**结论语境**里被引用且该行不带任何降级标记 ⇒ P2。

★ 设计取舍：
  - 只认**标识符**，不认自然语言关键词 ⇒ 精确可机判，避开 DIS-009 那类元描述误报
  - 标识符空间由「降级行」决定（不是全文扫描）⇒ 不会把正文里随便出现的 `P-010` 当靶
  - 结论行若已带降级标记（同词表）⇒ 不报，即「降级已传播」视为合规
  - 章节归属靠**标题语义词**而非硬编码 §N ⇒ RESEARCH/DESIGN/CHECKLIST 结构不同也能用

不变式：I-1 只读 / I-2 确定性（无 wall clock、同输入同输出）/ I-3 零新规则（只执行既有纪律）
        / I-4 判据可红（selftest 必含先验红 + 先验绿）

退出码：0 无违规 / 1 有违规 / 2 工具自身错误
用法：
    python scripts/degradation_gate.py                    # 全仓
    python scripts/degradation_gate.py file1.md file2.md  # 指定文件（pre-commit staged 语义）
    python scripts/degradation_gate.py --selftest         # 内嵌双用例
"""
from __future__ import annotations

import argparse
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ★ 降级标记词表——只收「明确声明未验」的强词。
# 曾把 ⚠ / ◐ / E4 / 单源 也算降级标记，真实语料跑出 27 条中大半误报（⚠ 在本文档体系里
# 是通用强调符，不代表未验）⇒ 收紧。
# ⚠ 但收紧**过头**也会误报：文档实际写的是「完全未验」「回原文后复核」，若词表只有
#   「未验证」「待复核」就漏匹配 ⇒ 保留「未验」「复核」「待核」这三个可作前缀的短形。
DEGRADERS = ("未验", "未取证", "未实测", "未确认", "待二核", "复核", "待核",
             "依赖假设", "E5", "无实测", "禁止入判据", "未回原文")

# 结论语境标题词：命中即进入「结论区」
CONCLUSION_HEAD = re.compile(
    r"^#{2,4}\s*.*(结论|关键发现|对设计的输入|对实施的输入|关键约束|综合分析|landscape|定位|技术 landscape)",
    re.I)
# 任意标题（用于退出结论区）
ANY_HEAD = re.compile(r"^#{1,6}\s")

# 标识符：字母(1-3) + 可选连字符 + 1-2 位数字。大小写敏感。
ID_RE = re.compile(r"\b([A-Z]{1,3}-?\d{1,2})\b")
# 排除噪声：批次号、证据等级（E1-E5 是分级不是条目）、闸门号、修订项号、设计决策号、不变式号
ID_BLACKLIST_PREFIX = ("P-", "ADR-", "DIS-", "DC", "FWK", "RULE-", "PT-",
                       "E1", "E2", "E3", "E4", "E5",
                       "G0", "G1", "G2", "G3", "G4", "G5",
                       "R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8", "R9",
                       "D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8",
                       "I-1", "I-2", "I-3", "I-4", "I-5", "I-6", "I-7", "I-8")

# ★ 条目位：只有出现在「表格首列」或「粗体列表项」位置的 ID 才算被降级的条目。
#   真实语料教训：不限定位次时，正文里随便提到的 G0/R1/D6 全被误登记为已降级条目。
ENTRY_POS_RE = re.compile(r"^\s*\|?\s*\*{0,2}([A-Z]{1,3}-?\d{1,2})\*{0,2}\s*(\||:|\*\*)")


def _entry_id(line: str) -> set:
    """该行是否为「条目定义行」（表格首列 / 粗体项），是则返回其 ID。"""
    m = ENTRY_POS_RE.match(line)
    if not m:
        return set()
    tok = m.group(1)
    return set() if any(tok.startswith(x) for x in ID_BLACKLIST_PREFIX) else {tok}


def _ids_of(line: str) -> set:
    """结论区引用检测：行内任意位置出现的 ID。"""
    out = set()
    for m in ID_RE.finditer(line):
        tok = m.group(1)
        if any(tok.startswith(x) for x in ID_BLACKLIST_PREFIX):
            continue
        out.add(tok)
    return out


def _is_degraded(line: str) -> bool:
    return any(d in line for d in DEGRADERS)


def check_file(rel: str, text: str) -> list:
    """返回 [(severity, line_no, message)]。"""
    lines = text.splitlines()
    degraded_ids = {}   # id -> 首次出现的降级行号
    in_conclusion = False
    for i, ln in enumerate(lines, 1):
        if CONCLUSION_HEAD.match(ln):
            in_conclusion = True
            continue
        if ANY_HEAD.match(ln):
            in_conclusion = False
        if _is_degraded(ln):
            for tok in _entry_id(ln):          # ★ 只登记「条目位」的 ID
                degraded_ids.setdefault(tok, i)
    if not degraded_ids:
        return []

    viol, in_conclusion = [], False
    seen = set()
    for i, ln in enumerate(lines, 1):
        if CONCLUSION_HEAD.match(ln):
            in_conclusion = True
            continue
        if ANY_HEAD.match(ln):
            in_conclusion = False
        if not in_conclusion or _is_degraded(ln):
            continue
        for tok in _ids_of(ln):
            if tok in degraded_ids and (tok, i) not in seen:
                seen.add((tok, i))
                viol.append(("P2", i,
                             f"结论区引用 {tok} 无降级标记（该标识符在 L{degraded_ids[tok]} "
                             f"已被标为未验证/未取证）"))
    return viol


def gather_md(root=ROOT):
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in
                       (".git", "__pycache__", ".pytest_cache", "tmp", "node_modules")]
        for fn in filenames:
            if fn.endswith(".md"):
                out.append(os.path.relpath(os.path.join(dirpath, fn), root))
    return sorted(out)


# ---------------- selftest：先验红 + 先验绿（I-4） ----------------
_RED = """# t
## 3. 发现
| B9 | 官方口径 | E3 转述，**未验证** |
## 4. 综合分析
### 4.1 关键发现总结
- 依据 B9 ⇒ 只能走 bf16 LoRA
"""
_GREEN = """# t
## 3. 发现
| B9 | 官方口径 | E3 转述，**未验证** |
## 4. 综合分析
### 4.1 关键发现总结
- 依据 B9 `[依赖假设 A-2]` ⇒ 只能走 bf16 LoRA
"""
# 反例：标识符出现在正文但结论区没引用 ⇒ 不该报
_NOUSE = """# t
## 3. 发现
| B9 | 官方口径 | 未验证 |
## 4. 综合分析
### 4.1 关键发现总结
- 与本标识符无关的一句话
"""


def selftest() -> int:
    ok = True

    def expect(cond, name):
        nonlocal ok
        print(("  PASS " if cond else "  FAIL ") + name)
        ok = ok and cond

    r = check_file("t.md", _RED)
    expect(len(r) == 1 and r[0][0] == "P2", "F1 先验红：结论引用未验标识符 ⇒ 报 P2")
    expect("B9" in r[0][2] if r else False, "F2 红例点名 B9")

    g = check_file("t.md", _GREEN)
    expect(g == [], "F3 先验绿：结论行已带降级标记 ⇒ 不报（证它不是恒真）")

    n = check_file("t.md", _NOUSE)
    expect(n == [], "F4 结论区未引用该标识符 ⇒ 不报（控误报）")

    # 批次号噪声不得当靶
    noise = "# t\n## 3 发现\nB9 未验证\n## 4 结论\n本批为 P-010 收口\n"
    expect(check_file("t.md", noise) == [], "F5 P-010 等批次号不当靶")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(prog="degradation_gate")
    ap.add_argument("files", nargs="*")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    files = a.files or gather_md()
    n_viol = 0
    for f in files:
        full = f if os.path.isabs(f) else os.path.join(ROOT, f)
        if not os.path.isfile(full):
            continue
        try:
            text = open(full, encoding="utf-8").read()
        except (OSError, UnicodeDecodeError) as e:
            print(f"[tool-error] {f}: {e}", file=sys.stderr)
            return 2
        for sev, ln, msg in check_file(f, text):
            print(f"[{sev}] {f}: {msg} (L{ln})")
            n_viol += 1
    if n_viol:
        print(f"降级传播检查失败：{n_viol} 违规")
        return 1
    print(f"降级传播检查通过：{len(files)} 文件，0 违规")
    return 0


if __name__ == "__main__":
    sys.exit(main())
