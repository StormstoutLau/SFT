# ADR-0001: 规范载体——宪法文档用指针，可执行件用副本

---
id: ADR-0001
type: adr
version: 1.0
status: accepted
date: 2026-11-11
depends: []
upstream: null
---

> **Feature**: P-001 骨架自举
> **创建日期**: 2026-11-11
> **状态**: accepted
> **适用**: 本仓与 `F:\Spec_Workflow` 之间的规范载体边界——哪些文档复制、哪些只指

---

## 元数据

| 字段 | 值 |
|------|-----|
| 编号 | ADR-0001 |
| 日期 | 2026-11-11 |
| 状态 | accepted |
| 决策者 | Scott（鹏）裁决「指针引用」；执行 = Claude Opus 5 |
| 相关文档 | `F:\Spec_Workflow\SPEC_PROCESS.md` v1.7.2（权威源）· `F:\Spec_Workflow\adr\ADR-0006-assertion-framework-dual-copy-authority.md`（双副本先例）· `F:\Spec_Runner\spec_runner.py` v1.0.0 |
| 取代 | 无 |

**证据等级约定（本仓沿用 Spec_Workflow 口径，按可重放性分级）**: E1=可重放命令 / E2=运行时脚本取证 / E3=静态读码绑 commit hash / E4=盲区扫描或判断 / E5=推测（禁止入审计结论）。

> ⚠ **口径冲突已登记**：`D:\RPC` 仓的 `E1-E4` 是按**会话来源**分级（E1=本会话实测 / E3=外部文档），与本仓语义不同。跨仓读到的 `E3` 须先确认是哪一套。

## 范围声明（先于一切）

**本决策仅约束「规范文档在本仓的存放形态」，不改变规则内容本身，也不改变门禁判据。** 规则语义、词表、档位判据的权威源始终在 `F:\Spec_Workflow`。

## 背景（Context）

### 触发实例

用户 2026-11-11 裁决 D:\SFT「完全自举」沿用 Spec_Workflow，并在载体形态三选一中选 **指针引用**。

### 根因

Spec_Workflow 自己已经为"双副本"付过代价——`ADR-0006` 整份 ADR 就是为裁决断言框架的两份并存副本而写。若本仓再把 `SPEC_PROCESS.md`（601 行）复制一份，就产生第三副本，且本仓无人有权限跟进上游 v1.7.x 的连续修订（P-108 / P-112 / P-113 / P-116 / P-163 五次修订集中在 2026-10-21 至 2026-11-08）。

## 决策（Decision）

### 1. 宪法层用指针（不复制）

`SPEC_PROCESS.md` / `docs/ASSERTION_EVIDENCE_FRAMEWORK.md` / `docs/DECISION_RECORD_CONTRACT.md` 三份**不在本仓建副本**。本仓 `AGENTS.md` 只写「指针 + 最小摘要」，权威源路径逐字写明。

### 2. 可执行件用副本（必须复制）

`scripts/` 六个校验器 + `spec/templates/` 六份模板**复制进本仓**。理由：`dc_validator.py` 的 `ROOT` 由 `__file__` 派生（E3：`scripts/dc_validator.py` L29@上游），跨仓调用会让门禁证据落在别的仓；模板需本地可改以适配本仓命名空间。

### 3. 本仓差异就地登记，不回改上游

凡本仓与上游形态不同处（M7 样本序列独立计数、DIS 编号空间自 100 起、`console_gen` 的 session 前缀），在 `spec/m7-hits-block/M7_HITS_DESIGN.md` 这类**本仓说明文档**里记差异，不改上游、不在本仓伪造"与上游一致"。

### 机制原理（为何有效）

指针使规则单点真值——上游修订即刻生效，本仓无滞后窗口；副本只落在"必须本地可执行"的件上，而可执行件的正确性由门禁自证（跑不过就报红），漂移会被机械暴露而非静默累积。

### 与既有 ADR/规则的关系

承 `SPEC_PROCESS` 设计原则「先有真值，再有派生视图」与「同一事实绝不两处定义」。

## 考虑的替代方案（Alternatives Considered）

### 替代方案 A: 全部复制（否决）

代价：三份宪法文档 × 每次上游修订 = 人工同步义务，且无门禁可拦（本仓没有 dc_validator 的 DC5 版本对账上游账面）。Spec_Workflow 为同类问题写过一整份 ADR-0006，重复该成本无收益。

### 替代方案 B: 全部指针，连校验器也不复制（推迟）

代价：门禁要在本仓跑，就得每次跨仓调用 `F:\Spec_Workflow\scripts\*.py`，其 `ROOT` 会指向上游仓 ⇒ 校验对象错位、证据落错仓。否决于"校验器"，但**模板**其实可归入此档，本批选择复制是为让本仓可独立改模板占位符。

## 后果（Consequences）

### 正面

规则零漂移；本仓门禁可独立跑；上游修订即刻生效。

### 负面

**F: 盘不可达时本仓自述不完整**——`AGENTS.md` 的摘要若与上游 v1.8+ 分叉，本仓无从察觉。缓解 = 摘要只写"最小操作面"，判断类问题一律回源。

### 中性 / 需要后续行动

本仓 `AGENTS.md` 必须显式写出权威源绝对路径与版本快照日期（否则指针悬空无人知）。

## 验证（Validation）

### 已有实证

- E1：`python scripts/dc_validator.py --check-all` 在本仓 exit 0（6 文件 / 1 跳过 / 0 违规）
- E1：`python scripts/m7_stats.py` exit 0（hits 块与机械重数一致）
- E3：`dc_validator.py` `ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))` ⇒ 复制即换根

### 待验证项

- `repo_stats.py` / `console_gen.py` 在本仓形态下能否 exit 0（pattern 库绑上游中文措辞，本仓需重写）
- 上游若改 DC2 词表，本仓副本校验器是否会在未同步时误判本仓文档

### 失效条件（何时重审本 ADR）

① `F:\Spec_Workflow` 不再是稳定可达的权威源（换机 / 归档）；② 本仓规则需求与上游分叉到需要独立词表；③ 出现"因指针不可达导致门禁误判"的实例。

## 修订历史

| 日期 | 版本 | 变更 |
|------|------|------|
| 2026-11-11 | v1.0 | 初版——宪法指针 / 可执行件副本 / 差异就地登记三分 |
