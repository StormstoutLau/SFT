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
| 4 | 2026-11-12 | P-002 RESEARCH.md（本仓，**RULE-5 异构审查轮**） | ★ **异基座**：审查者 `nvidia/nemotron-3-ultra-550b-a55b:free` vs 实现者 A 站 halogen `qwen 3.8 flash next`（跨家族，本仓首个异构臂） | 10（3P1+5P2+2P3）；实现者判定 = 成立 5 / 部分 3 / **不成立 2** | 3（**审查者自身**形态 II：章节号 2——引论文 §3.2/§4.3 细节但 abstract 无从支撑，疑生成填充；数值常量 1——按 16 CU 推 gfx1151 得 11.5 TFLOPS，实为 40 CU，低估约 4×） | docs/reviews/p002-research.adjudication.md |
| 5 | 2026-11-12 | P-006 DESIGN.md（本仓，**RULE-5 异构审查轮 2**） | 异基座 `nvidia/nemotron-3-ultra-550b-a55b:free`（`--mode design`）vs 实现者 halogen `qwen 3.8 flash next` | 8（2P1+4P2+2P3）；判定 = 成立 6 / 部分 2 / **不成立 0** | 0（★ 与轮 1 对照：本轮审查者零事实错误——疑因提示词新增「不要凭印象给硬件规格」约束，亦可能因设计文档多为内部一致性命题，**两因不可分离**） | docs/reviews/p006-design.adjudication.md |
| 6 | 2026-11-12 | P-002 RESEARCH §3.4-1（本仓，P-008 回原文复核轮） | 同基座自查（WebFetch 通道恢复后回官方文档，非独立审查臂） | 1（1P2） | 1（转述引文——采信 `D:\RPC` 二手记录「加速数据多在 colab/A100 测得」，未回原文即加强写成「Unsloth 官方数据全在 A100/Colab/N 卡」并据此判「无参照系」；实测官方文档明列 gfx1151 支持 LoRA 训练 ⇒ 二手转述被当一手结论用，且推理跳了一步） | spec/a1-smoke-test/RESEARCH.md §3.3 |
| 7 | 2026-11-12 | P-010 RESEARCH.md（本仓，**RULE-5 主动 pass**） | 异基座 `nvidia/nemotron-3-ultra-550b-a55b:free`（`--mode research`），收口前主动做、非补审 | 8（4P1+2P2+2P3）；判定 = **成立 8 / 部分 0 / 不成立 0** | 0（★ 本仓首次零驳回——但**不可归因于审查变准**：本档问题密度可能确实高，六条规律全靠 abstract、主结论单源） | docs/reviews/p010-pipeline.adjudication.md |

| 8 | 2026-11-12 | P-011 degradation_gate（本仓，门禁自测轮） | 机械三重验证（fixture 先验红/绿 + 真实语料全量 + **历史错误形态注入**） | 2（2P2） | 1（计数——首版把 ⚠/◐ 等通用强调符当降级标记，真实仓跑出 27 条而真靶仅约 1/3；收紧后又因词表漏「未验」「复核」前缀短形再错 2 条） | ADR-0002 §验证 |
| 9 | 2026-11-12 | P-012 DESIGN.md（本仓，RULE-5 主动 pass 轮 3） | 异基座 Nemotron 550B（`--mode design`），首调返回非 JSON、同通道重试即通 | 10（3P1+5P2+2P3）；判定 = 成立 9 / 部分 1 / **不成立 0** | 0（★ 连续第二轮零驳回；但**不可归因审查变准**——本仓文档问题密度随批次上升） | docs/reviews/p012-pipeline-design.adjudication.md |

## 2. 形态 II 复发分桶（载体 × 字段类型）

> 字段类型 = 形态 II 偏好的"精确-looking 低语义载荷"字段。

| 载体 \ 字段类型 | 版本号 | 章节号 | 数值常量 | 行号 | 计数 | 转述引文 | 映射闭合 | 小计 |
|---|---|---|---|---|---|---|---|---|
| Spec_Runner 版本判定（本仓 P-001 取证轮） | 1 | — | — | — | — | — | — | 1 |
| sft-bootstrap CHECKLIST 发现 2（本仓，ADD Phase 3 自审） | — | — | — | — | — | — | 1 | 1 |
| P-004 决策链锚点（本仓，verify-anchor 机检轮） | — | 6 | — | 1 | — | — | — | 7 |
| P-002 RESEARCH 异构审查轮（本仓，审查者侧形态 II） | — | 2 | 1 | — | — | — | — | 3 |
| P-002 §3.4-1 回原文复核（本仓，转述当一手） | — | — | — | — | — | 1 | — | 1 |
| P-011 门禁自测轮（本仓，判据宽严双向失准） | — | — | — | — | 1 | — | — | 1 |
| 合计 | 1 | 8 | 1 | 1 | 1 | 1 | 1 | 14 |

## 3. 规律锚点

（待样本累积后登记；本仓当前样本量不足以归纳规律。）

## 4. 候选登记

（无。）

## 5. 机读统计块（hits）

> 统计唯一声明处（R7 同构：声明 = 机械重数）。重生成：`python scripts/m7_stats.py --write`（校验先行 + 写守卫——失衡账本不可写入）；提交瞬间由 pre-commit hook `m7-stats` 自动校验。字段语义：[M7_HITS_DESIGN §4](../spec/m7-hits-block/M7_HITS_DESIGN.md)。

```hits
{
  "samples": 9,
  "form2_by_field": {
    "version": 1,
    "section": 8,
    "constant": 1,
    "line": 1,
    "count": 1,
    "quote": 1,
    "mapping": 1
  },
  "form2_total": 14,
  "form2_pre_ledger": 0,
  "form2_from_samples": 14,
  "findings": {
    "p1": 12,
    "p2": 27,
    "p3": 9,
    "unlabeled": 0,
    "cells_nonstandard": 0
  }
}
```
