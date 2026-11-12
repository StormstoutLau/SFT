---
id: SFT-M7
type: process-spec
version: 1.0
status: active
date: 2026-11-11
depends: [SFT-PROGRESS]
upstream: "F:\\Spec_Workflow\\docs\\M7_EVIDENCE_LOG.md"
---

# M7 证据账本（对比臂数据累积）

> **权威载体**: 本文件为 M7 数据本仓唯一活载体。登记纪律 = 每轮审查/审计完成后追加一行样本，形态 II 分桶随样本同步追加。
> **上游**: 框架定义见 `F:\Spec_Workflow\docs\ASSERTION_EVIDENCE_FRAMEWORK.md`（本仓以指针沿用）；本仓骨架说明见 [M7_HITS_DESIGN](../spec/m7-hits-block/M7_HITS_DESIGN.md)。
> **建立**: 2026-11-11（骨架自举批 P-001）

## 1. 样本登记表

| # | 日期 | 载体 | 审查配置 | 发现 | 形态II复发 | 来源 |
|---|------|------|---------|------|-----------|------|
| 1 | 2026-11-11 | Spec_Runner 版本判定（本仓 P-001 取证轮） | 同基座自查（Claude Opus 5 既写又审）→ 被 `git log` 实测推翻 | 1（1P2） | 1（版本号——采信 `tools/spec_runner/README.md` 的「外仓冻结为历史存档」声明，未查外仓 git log；实测最后提交 2026-11-10，且 sessions 含 factorv3/finagent/oe/macrodata 四项目活跃事件流） | P-001 取证轮 |
| 2 | 2026-11-11 | sft-bootstrap CHECKLIST §8.2 发现 2（本仓，ADD Phase 3 自审） | 同基座自查（审计臂自身无第二视角，RULE-4） | 1（1P3） | 1（映射闭合——判 `spec_map.py`「无门禁消费」时只查了 `.pre-commit-config.yaml` 的 files 正则，未查 `console_gen.py` L47 `import spec_map`；证据全真、推理跳步 = 形态 III，删除后经 `import console_gen` 实测恢复） | 本文件 §8.2 更正记录 |
| 3 | 2026-11-12 | P-004 决策链锚点（本仓，verify-anchor 机检轮） | **机械核查异构于生成端**（verify-anchor 纯脚本，非 LLM 自任验证器） | 7（7P2） | 7（章节号 6 + 行号 1——锚点章节名按文档标题字面凭印象写：`§决策` / `§待办事项` / `§命令面` / `文件头差异节` / `DIS-100` 无定位符 / 裸路径无定位符；另 1 处行号类 = 中文文件名不被锚点正则接受） | P-004 实施轮 |

## 2. 形态 II 复发分桶（载体 × 字段类型）

> 字段类型 = 形态 II 偏好的"精确-looking 低语义载荷"字段。

| 载体 \ 字段类型 | 版本号 | 章节号 | 数值常量 | 行号 | 计数 | 转述引文 | 映射闭合 | 小计 |
|---|---|---|---|---|---|---|---|---|
| Spec_Runner 版本判定（本仓 P-001 取证轮） | 1 | — | — | — | — | — | — | 1 |
| sft-bootstrap CHECKLIST 发现 2（本仓，ADD Phase 3 自审） | — | — | — | — | — | — | 1 | 1 |
| P-004 决策链锚点（本仓，verify-anchor 机检轮） | — | 6 | — | 1 | — | — | — | 7 |
| 合计 | 1 | 6 | 0 | 1 | 0 | 0 | 1 | 9 |

## 3. 规律锚点

（待样本累积后登记；本仓当前样本量不足以归纳规律。）

## 4. 候选登记

（无。）

## 5. 机读统计块（hits）

> 统计唯一声明处（R7 同构：声明 = 机械重数）。重生成：`python scripts/m7_stats.py --write`（校验先行 + 写守卫——失衡账本不可写入）；提交瞬间由 pre-commit hook `m7-stats` 自动校验。字段语义：[M7_HITS_DESIGN §4](../spec/m7-hits-block/M7_HITS_DESIGN.md)。

```hits
{
  "samples": 3,
  "form2_by_field": {
    "version": 1,
    "section": 6,
    "constant": 0,
    "line": 1,
    "count": 0,
    "quote": 0,
    "mapping": 1
  },
  "form2_total": 9,
  "form2_pre_ledger": 0,
  "form2_from_samples": 9,
  "findings": {
    "p1": 0,
    "p2": 8,
    "p3": 1,
    "unlabeled": 0,
    "cells_nonstandard": 0
  }
}
```
