---
id: sft-bootstrap-M7-HITS-DESIGN
type: design
version: 1.0
status: draft
date: 2026-11-11
depends: []
upstream: "F:\\Spec_Workflow\\spec\\m7-hits-block\\M7_HITS_DESIGN.md"
---

# M7 hits 机读块 · 本仓骨架说明

> **权威源**: 契约定义在 `F:\Spec_Workflow\spec\m7-hits-block\M7_HITS_DESIGN.md`（本仓以指针沿用，不复制副本）。
> 本文档只记本仓落地的差异面。

## 1. 本仓与权威源的差异

| 项 | Spec_Workflow | D:\SFT | 理由 |
|---|---|---|---|
| 样本序列 | 自 1 起，累计至 ㊳ | 自 1 起（本仓独立计数） | M7 是**本仓审查轮**的载体，跨仓不续号；上游累计数不并入 |
| `form2_pre_ledger` | 6 | 0 | 本仓无建账前遗留样本 |
| DIS 编号空间 | DIS-007~010（001-006 留源项目） | DIS-100 起 | 避开 Spec_Workflow 与 Cpp_Hub 两个已占区间 |

## 2. 校验入口

```bash
python scripts/m7_stats.py            # verify（只读对账）
python scripts/m7_stats.py --write    # 校验先行 + 重生成 §5 hits 块
```

表结构常量（`SAMPLE_COLS` / `BUCKET_COLS` / `HITS_TOP_KEYS`）逐字符沿用上游，未改 ⇒ 本仓 M7 表头必须与上游同形，否则 P1。

## 3. 未决项登记（四元块）

| 判据 | 触发条件 | 当前倾向 | 证据等级 |
|---|---|---|---|
| 本仓 M7 是否与 Spec_Workflow 合并成单一账本 | 出现首个需要跨仓对比臂的批次 | 不合并——账本与本仓审查轮同处才满足「证据与载体同仓」 | E4（推断） |
