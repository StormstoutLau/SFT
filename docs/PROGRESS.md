---
id: SFT-PROGRESS
type: process-spec
version: 1.0
status: active
date: 2026-11-11
depends: [ADR-0001]
upstream: null
---

# PROGRESS 待办登记

> 依据 SPEC_PROCESS 约定建立。状态词表: `pending / in-progress / blocked / done`。
> **权威源**: 流程宪法 = `F:\Spec_Workflow\SPEC_PROCESS.md`（本仓以指针沿用，不复制副本 · 裁决见 [ADR/0001](../adr/ADR-0001-规范载体为指针而非副本.md)）。
> **登记时点纪律**: 立项即登记——新批次开工前先登记 P 行，执行态不人写。
> **建立**: 2026-11-11（骨架自举批）

## 待办事项

| ID | 事项 | 依据 | 状态 | 优先级 | 验收标准 |
|----|------|------|------|--------|---------|
| P-001 | D:\SFT 骨架自举——目录树 + 台账 + 校验器 + pre-commit + Spec_Runner 接入 | 用户裁决 2026-11-11「完全自举 / 接 runner 并挂 Review / 出网异构」· [ADR-0001](../adr/ADR-0001-规范载体为指针而非副本.md) | done | P0 | 逐项实测（详见 [CHECKLIST §10.1](../spec/sft-bootstrap/CHECKLIST.md)）：① dc_validator exit 0 ✅ ② m7_stats exit 0 ✅ ③ repo_stats exit 0 ✅ ④ probe 入流 + replay 通过 ✅ ⑤ pre-commit 已 install，**4/4 Passed** ✅ ⑥ 四文档齐 ✅ ⑦ 五步决策链 + verify-anchor 全真实 ✅（step-enforce 的两处阻断经 P-004 修复：前缀硬编码 + decision 写入口缺失） |
| P-002 | 分布式微调可行性正式调研（RESEARCH） | [RESEARCH](../spec/distributed-sft/RESEARCH.md) · 上一轮对 `D:\RPC` 的只读取证（未成文）· 记忆条目 `rpc-cluster-training-verdict` | in-progress | P1 | 逐项实测：F1 来源日期 ✅（读取日 2026-11-12 + 发布/更新日分列）· F2 版本 ✅（18 条 arXiv 含 vN + 仓内件绑 blob hash）· F3 降级链 ✅（english-search 522×3 / WebFetch 拦 / 两站点 0 命中全登记）· F4 引用表 ✅（20 行，含 2 条未验证行显式标态）· F5 = N/A（纯文档批）· 断言标 A/B/C ✅ · **未过**：DESIGN/IMPL/CHECKLIST 未开（Step 3+）；B1/B3/B5 单源待二核 |
| P-003 | 三站 RCCL 训练前置实测（跨机吞吐 / world_size=3 / A 站补装） | P-002 结论待定 | blocked | P2 | 三站在线后可做；当前 ping 全不通（2026-11-11 实测） |
| P-004 | runner 升级 v1.0.0→v1.11.0 + step_enforce 前缀修复 + decision 写入器 | [decisions](../spec/runner-upgrade/decisions.json) · DIS-101 · 用户裁决 2026-11-12「换 runner v1.11.0 复制进本仓」 | done | P0 | 逐项实测：① `--version` = 1.11.0 ✅ ② `sessions_dir()` 落本仓 ✅ ③ step-gate 5/5 pass exit 0 ✅ ④ verify-anchor 13 锚点全真实 exit 0 ✅ ⑤ step_enforce 对 P-001/P-002 通过 ✅ ⑥ DIS-102 登记 ✅ |
| P-005 | RULE-5 异构审查：用 OpenRouter 非 Qwen 家族审 RESEARCH.md | [review-decisions](../spec/distributed-sft/review-decisions.json) · [adjudication](../docs/reviews/p002-research.adjudication.md) · [review 取证](../docs/reviews/p002-research.review.md) · 用户指令 2026-11-12「从 RPC 调取主控站 OpenRouter API 完成异构审查」 | done | P1 | 逐项实测：① 审查者基座 = `nvidia/nemotron-3-ultra-550b-a55b:free`，与实现者（A 站 halogen qwen 3.8 flash next）**异家族** ✅ ② E1 usage 读数 prompt 8696 / completion 6796 / reasoning 2724，cost 0 ✅ ③ 10 条发现逐条判定：5 成立 / 3 部分 / **2 不成立**（审查者自报 CU 数与章节号均错）✅ ④ 成立项全部落 RESEARCH v1.2（R1-R8）✅ ⑤ key 运行时读 `D:\RPC\secrets\`，未落本仓 ✅ |

## 依赖链

```
P-001（骨架）→ P-002（调研）→ P-003（实测）
```

## 档位声明

本仓批次档位判定沿用 `SPEC_PROCESS.md` §批次档位与裁剪理由：改动路径 ∩ {`scripts/`,`tests/`,`tools/`,`.pre-commit-config.yaml`,`.github/workflows/`} = ∅ → Layer-0 → T3；否则 T1。P-001 命中 `scripts/` + `.pre-commit-config.yaml` ⇒ **T1 完整管线**。
