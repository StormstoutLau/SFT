# DEV-LOG-002 — P-002 调研落档 + P-004 runner 升级

> **日期**: 2026-11-12 · **批次**: P-002（调研批）+ P-004（工具链批）
> **执行**: Claude Opus 5 · **裁决**: Scott（鹏）

## 做了什么

**P-002**：把上一轮口头分析落成 `spec/distributed-sft/RESEARCH.md` v1.1，并按 F1-F5 出具；社区检索取到 18 篇 arXiv T1 源，映射出 L0-L5 六层方案梯度。

**P-004**：runner 从 `F:\Spec_Runner` v1.0.0 升级为**本仓副本 v1.11.0**（`tools/spec_runner/`），修 `step_enforce` 前缀硬编码，新建 `scripts/sft_decision.py` 补 decision 写入口，三条批次链（P-001/P-002/P-004）建成并全绿。

## 决策依据

P-004 起因 = P-001 收口时 `step_enforce` 恒报「P 行无 session」。取证见 DIS-101：`step_enforce.py` L129 硬编码 `specwf-` 前缀 + L195 要求 `decision` 事件，而 v1.0.0 两者皆无。用户裁「换 v1.11.0 复制进本仓」。

## 过程中的自我更正（三条，全部留痕）

| # | 原判断 | 更正 | 手段 |
|---|---|---|---|
| 1 | 「换 v1.11.0 就能出 decision 链」 | v1.11.0 的 `cmd_run` 只写 prompt/llm_request/llm_response，**31 处 decision append 全在 selftest fixture** ⇒ CLI 仍无写入口，须自建 | 读 `cmd_run` 实现 + grep append |
| 2 | 「step_enforce exit 0 证实只是空仓鸡生蛋」 | 当时 P-002 是 `pending` 被豁免；转 `in-progress` 才撞上真问题。该表述已收窄 | 读 `resolve()` 的 `changed_pids` 逻辑 |
| 3 | 决策链锚点 7 处写成模糊串（`§决策` / `文件头差异节` / `DIS-100` 无定位符 / 中文文件名 `#L49`） | 全部改为可解析形态或改指 ASCII 名落点，`note` 留原锚 | **verify-anchor 机检**（非 LLM 自查） |

## 门禁读数（E1，可重放）

```
DC contract validator (DC1-DC5 + R7)....Passed
M7 ledger hits block validator..........Passed
View-layer enumeration validator........Passed
Step decision-stream enforcement........Passed
step-gate[sft-p001-bootstrap-20261112]: 决策链一致 pass → exit 0
verify-anchor[...]: 锚点 13 真实 / 0 硬性 / 0 软性 → exit 0
m7_stats --write: samples=3, form2_total=9
```

## 新发现登记

- **DIS-101**：上游门禁件把环境态写成常量（前缀硬编码），跨仓沿用时恒不匹配而非报错
- **DIS-102**：`verify-anchor` 锚点正则不接受非 ASCII 文件名 ⇒ 中文命名文档永远无法作机检锚点

## 下一步

- P-002 的 Step 3+（DESIGN / IMPLEMENTATION / CHECKLIST）另立批次
- P-003 三站实测仍 `blocked`（离线）
- RULE-5 异构第二视角（出网 API）仍未接——本批全部标 `自查（单视角）`
