# 设计文档：sft-bootstrap（骨架自举）

---
id: sft-bootstrap-DESIGN
type: design
version: 1.0
status: draft
date: 2026-11-11
depends: [sft-bootstrap-RESEARCH, ADR-0001]
upstream: null
---

## 1. 设计目标

在 `D:\SFT` 建一个**门禁真能跑**的最小自举骨架，使后续 P-002（微调调研）能直接进 Step 1，而不是先解决工具链。

## 2. 关键决策

| # | 决策 | 理由 | 代价 |
|---|---|---|---|
| D1 | 宪法文档（SPEC_PROCESS / ASSERTION / DECISION_RECORD）**只留指针**，本仓不复制 | 规则单点真值；上游 2026-10-21→11-08 五次修订，副本必滞后 | F: 盘不可达时本仓自述不完整 |
| D2 | 校验器与模板**复制进本仓** | `ROOT` 由 `__file__` 派生，跨仓调用会让证据落错仓 | 第三副本，无同步门禁 |
| D3 | runner 用 `F:\Spec_Runner` **v1.0.0 引用**，sessions 用 `SR_SESSIONS_DIR` 注入回本仓 | 零副本 + 证据与本仓同处 + 照 factorv3 先例 | RULE-1 补的 `decision`/`verify-anchor` 取证**物理缺失**，须逐轮标降级 |
| D4 | hooks 取 **4** 道，不接 console-gen / blackbox-tests | 前者硬编码 `specwf-` 前缀需改常量；后者 `tests/` 尚空无对象 | 视图派生面与 runner 回归保护缺位（已登记） |
| D5 | M7 样本序列**本仓独立从 1 计数**，DIS 编号自 **100** 起 | 账本与审查轮同仓才有可核性；100 段避开上游 007-010 与 Cpp_Hub 001-006 | 跨仓对比臂需人工并表 |
| D6 | `repo_stats` 的 pattern 库**只放本仓真实措辞**（2 条），不照抄上游 20 条 | 抄来的 pattern 匹配不到本仓文本 = 恒真门禁，正是「判据必须命得中」要防的 | 视图层覆盖面远小于上游 |

## 3. 拒绝的替代方案

| 方案 | 拒绝理由 | 承认可见的代价 |
|---|---|---|
| 全部复制（含宪法） | 三文档 × 每次上游修订 = 无门禁兜底的人工同步义务 | 本仓离线可读性更好 |
| 全部指针（含校验器） | 证据落错仓，`step_enforce` 看不见本仓 session | 零副本 |
| 复制 v1.11.0 runner | 第四副本，且本仓当前不需要 `step-gate` | RULE-1 补可完整出具 |
| 照抄上游 20 条 pattern | 恒真门禁——扫不到任何靶却显示绿，比没有门禁更危险 | 视图漂移无人拦 |

## 4. 目录契约

```
D:\SFT\
├── AGENTS.md              指针 + 最小摘要（D1）
├── CODE_WIKI.md           §10 stats 块 = 视图声明唯一登记处
├── README.md              facade
├── .pre-commit-config.yaml 4 hooks（D4）
├── adr/ADR-0001-*.md      载体裁决
├── docs/{PROGRESS,M7_EVIDENCE_LOG}.md  真值源
├── docs/discoveries/README.md          DIS-100 起
├── scripts/               7 件（6 校验器 + adapter）
├── spec/templates/        6 模板
├── spec/sft-bootstrap/    本批四文档
└── tools/spec_runner/sessions/   SR_SESSIONS_DIR 落点（D3）
```

## 5. 不变式

- **I-1** 门禁必须真跑：任何"绿"须有可重放命令支撑（E1），不接受自述
- **I-2** 缺口如实登记：v1.0.0 取证缺失、console-gen 未接、三站离线——三处必须在门面可见，不得被"骨架完成"掩盖
- **I-3** 视图声明 = 机械重数：`CODE_WIKI §10` 的 `declared` 由 `repo_stats` 对账，改文件必改声明
- **I-4** 本仓不改上游件语义：复制件的差异须在本仓文档登记

## 6. 新增面自查（ADR-0010 三问）

| 问 | 答 |
|---|---|
| 这个新增面是必需的吗 | 是——无门禁则 RULE-6 的证据绑定无载体 |
| 能否用既有机制承载 | 否——本仓原为空目录，无既有门禁 |
| 它会不会成为第二个做同一件事的入口 | 否——四道校验器各管一域，与上游同构 |
