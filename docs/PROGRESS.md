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
| P-002 | 分布式微调可行性正式调研（RESEARCH） | [RESEARCH](../spec/distributed-sft/RESEARCH.md) · 上一轮对 `D:\RPC` 的只读取证（未成文）· 记忆条目 `rpc-cluster-training-verdict` | done | P1 | 逐项实测：F1 来源日期 ✅（读取日 2026-11-12 + 发布/更新日分列）· F2 版本 ✅（18 条 arXiv 含 vN + 仓内件绑 blob hash）· F3 降级链 ✅（english-search 522×3 / WebFetch 拦 / 两站点 0 命中全登记）· F4 引用表 ✅（20 行，含 2 条未验证行显式标态）· F5 = N/A（纯文档批）· 断言标 A/B/C ✅ · **未过**：DESIGN/IMPL/CHECKLIST 未开（Step 3+）；B1/B3/B5 单源待二核 **未过项已消**：DESIGN 已另立 P-006 完成；P-002 范围界定为调研批（Step 1-2），已收口 |
| P-003 | 三站 RCCL 训练前置实测（跨机吞吐 / world_size=3 / A 站补装） | P-002 结论待定 | blocked | P2 | 三站在线后可做；当前 ping 全不通（2026-11-11 实测） |
| P-004 | runner 升级 v1.0.0→v1.11.0 + step_enforce 前缀修复 + decision 写入器 | [decisions](../spec/runner-upgrade/decisions.json) · DIS-101 · 用户裁决 2026-11-12「换 runner v1.11.0 复制进本仓」 | done | P0 | 逐项实测：① `--version` = 1.11.0 ✅ ② `sessions_dir()` 落本仓 ✅ ③ step-gate 5/5 pass exit 0 ✅ ④ verify-anchor 13 锚点全真实 exit 0 ✅ ⑤ step_enforce 对 P-001/P-002 通过 ✅ ⑥ DIS-102 登记 ✅ |
| P-005 | RULE-5 异构审查：用 OpenRouter 非 Qwen 家族审 RESEARCH.md | [review-decisions](../spec/distributed-sft/review-decisions.json) · [adjudication](../docs/reviews/p002-research.adjudication.md) · [review 取证](../docs/reviews/p002-research.review.md) · 用户指令 2026-11-12「从 RPC 调取主控站 OpenRouter API 完成异构审查」 | done | P1 | 逐项实测：① 审查者基座 = `nvidia/nemotron-3-ultra-550b-a55b:free`，与实现者（A 站 halogen qwen 3.8 flash next）**异家族** ✅ ② E1 usage 读数 prompt 8696 / completion 6796 / reasoning 2724，cost 0 ✅ ③ 10 条发现逐条判定：5 成立 / 3 部分 / **2 不成立**（审查者自报 CU 数与章节号均错）✅ ④ 成立项全部落 RESEARCH v1.2（R1-R8）✅ ⑤ key 运行时读 `D:\RPC\secrets\`，未落本仓 ✅ |
| P-006 | L0 方案定形（DESIGN，Step 3-4） | [DESIGN](../spec/distributed-sft/DESIGN.md) · [adjudication](../docs/reviews/p006-design.adjudication.md) · 用户指令 2026-11-12「开 P-002 的 DESIGN，把 L0 方案定形」 | done | P1 | 逐项实测：① DESIGN v1.0 落盘（架构/接口/数据结构/I-1~I-6/替代方案 A-D）✅ ② §9.1-9.4 Step 4 Review 含归因扭曲单列 ✅ ③ **RULE-1 独立 pass 已做**（`--mode design` 异构审查，prompt 6017 / completion 8046 / reasoning 5330）✅ ④ 8 条发现判定 = 6 成立 / 2 部分 / **0 不成立** ✅ ⑤ R1-R8 全落 DESIGN v1.1（新增 orchestrate 模块 + A-7/A-8/A-9）✅ ⑥ dc_validator 27 文件 0 违规 ✅ ⑦ **A-9 已裁并落 DESIGN v1.2**（用户裁「本批只出设计不实跑」）✅ |
| P-007 | Step 5+ 实施（IMPLEMENTATION / CHECKLIST / TDD） | [DESIGN §10.1 第 0 条](../spec/distributed-sft/DESIGN.md) · A-9 裁决 2026-11-12「本批只出设计不实跑」 | blocked | P1 | 前置未满足：① 三站离线（2026-11-11 ping 全不通）② **A-1 未验**（Unsloth 在 gfx1151 能否训练，单点否决闸）③ A-9 已裁延后 ⇒ 重判条件 = 三站上线且 A-1 冒烟获准。⚠ 硬件到位前本仓可推进极限为纸面工件，**不得用「已实现」描述任何未跑过的环节** |
| P-008 | A-1 冒烟测试设计（充分参考社区案例与 RPC 实际经验） | [RESEARCH](../spec/a1-smoke-test/RESEARCH.md) · [DESIGN](../spec/a1-smoke-test/DESIGN.md) · 回写 [distributed-sft RESEARCH v1.3](../spec/distributed-sft/RESEARCH.md) 与 [DESIGN v1.3](../spec/distributed-sft/DESIGN.md) · 用户指令 2026-11-12「把 A-1 冒烟测试设计出来」 | done | P1 | 逐项实测：① 官方 T1 取证 13 条（U1-U13，WebFetch `?ask=` 实取）✅ ② `D:\RPC` 本集群经验 8 条（R1-R8 绑 blob hash）✅ ③ ★ 三条推翻性发现：官方**明列 gfx1151 支持 LoRA**（推翻本仓 P-002「官方数据全在 A100/Colab」）· MoE 4-bit 限制仅对 unmodified bnb 成立 · 4-bit 冒烟不验 bf16 ⇒ 双臂强制 ✅ ④ 六闸门设计（G0-G5）每条判据配先验红 + 退出码三分 ✅ ⑤ 回写 RESEARCH v1.3 / DESIGN v1.3（A-1 由 E5 降为待复现）✅ ⑥ M7 样本 6 入账 ✅ ⑦ 四道门禁 Passed ✅ |

## 依赖链

```
P-001（骨架）→ P-002（调研）→ P-003（实测）
```

## 档位声明

本仓批次档位判定沿用 `SPEC_PROCESS.md` §批次档位与裁剪理由：改动路径 ∩ {`scripts/`,`tests/`,`tools/`,`.pre-commit-config.yaml`,`.github/workflows/`} = ∅ → Layer-0 → T3；否则 T1。P-001 命中 `scripts/` + `.pre-commit-config.yaml` ⇒ **T1 完整管线**。
