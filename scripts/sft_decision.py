#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""decision 事件写入器 —— 补 v1.11.0 的 CLI 缺口（DIS-101 延伸）

为什么需要：`step_enforce` 的 batch 模式要求「至少一个 session 有完整 5/5 decision 链」，
但 `spec_runner.py` v1.11.0 的 `run` 只写 prompt/llm_request/llm_response，
**没有任何 CLI 入口能写 `decision` 事件**（31 处 decision append 全在 selftest fixture 内）。
本脚本复用 runner 自己的 `EventWriter`，从而继承其写入端把守（schema / seq 单调 / append-only），
不另造第二套写入语义。

字段形态 = FWK-DECISION-RECORD 八字段 + metadata.{step_id, step_seq, evidence}，
对齐 `F:\Spec_Workflow\docs\DECISION_RECORD_CONTRACT.md` §1。

用法：
    python scripts/sft_decision.py --session sft-p001-bootstrap-20261112 --file decisions.json
    python scripts/sft_decision.py --session ... --file ... --dry-run

decisions.json 形态（数组，每元素一步）：
    [{"step_id":"research","step_seq":1,"category":"...","scenario":"...",
      "reasoning":"...","outcome":"...",
      "evidence":[{"grade":"E1","anchor":"spec/x/RESEARCH.md §3"}]}]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools" / "spec_runner"))

from spec_runner import EventWriter, sessions_dir  # noqa: E402

REQUIRED = ("step_id", "step_seq", "category", "scenario", "reasoning", "outcome", "evidence")


def build_input(item: dict) -> dict:
    missing = [k for k in REQUIRED if k not in item]
    if missing:
        raise ValueError(f"decision 缺字段: {missing}")
    ev = item["evidence"]
    if not isinstance(ev, list) or not ev:
        raise ValueError("evidence 必须为非空数组（step-gate 判据）")
    for e in ev:
        if not isinstance(e, dict) or "grade" not in e or "anchor" not in e:
            raise ValueError(f"evidence 条目须含 grade + anchor: {e!r}")
    return {
        "category": item["category"],
        "scenario": item["scenario"],
        "reasoning": item["reasoning"],
        "outcome": item["outcome"],
        "confidence": item.get("confidence", 0.9),
        "entities": item.get("entities", []),
        "decision_maker": item.get("decision_maker", ""),
        "metadata": {
            "step_id": item["step_id"],
            "step_seq": item["step_seq"],
            "evidence": ev,
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(prog="sft_decision", description="decision 事件写入器")
    ap.add_argument("--session", required=True)
    ap.add_argument("--file", required=True, help="decision 数组 JSON")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    try:
        items = json.loads(Path(a.file).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        print(f"sft_decision: 读取失败 {e}", file=sys.stderr)
        return 2
    if not isinstance(items, list) or not items:
        print("sft_decision: 输入须为非空数组", file=sys.stderr)
        return 2

    built = []
    for i, it in enumerate(items, 1):
        try:
            built.append(build_input(it))
        except ValueError as e:
            print(f"sft_decision: 第 {i} 条非法: {e}", file=sys.stderr)
            return 2

    if a.dry_run:
        for b in built:
            m = b["metadata"]
            print(f"[dry] step={m['step_id']} seq={m['step_seq']} "
                  f"evidence={len(m['evidence'])} outcome={b['outcome'][:60]}")
        return 0

    w = EventWriter(sessions_dir())
    for b in built:
        row = w.append(a.session, "assistant", "decision", input_=b)
        print(f"appended seq={row['seq']} step={b['metadata']['step_id']}")
    print(f"sft_decision: {len(built)} 条已写入 {a.session}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
