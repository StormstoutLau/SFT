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
| P-001 | D:\SFT 骨架自举——目录树 + 台账 + 校验器 + pre-commit + Spec_Runner 接入 | 用户裁决 2026-11-11「完全自举 / 接 runner 并挂 Review / 出网异构」· [ADR-0001](../adr/ADR-0001-规范载体为指针而非副本.md) | in-progress | P0 | 逐项实测（详见 [CHECKLIST §10.1](../spec/sft-bootstrap/CHECKLIST.md)）：① dc_validator exit 0 ✅ ② m7_stats exit 0 ✅ ③ repo_stats exit 0 ✅ ④ probe 入流 + replay 通过 ✅ ⑤ pre-commit 已 install，4 道中 3 Passed ⚠ ⑥ 四文档齐 ✅。**未过项 = step-enforce exit 2**，根因空仓无 `HEAD` ⇒ 待首次 commit 后复核，不标 `done` |
| P-002 | 分布式微调可行性正式调研（RESEARCH） | 上一轮对 `D:\RPC` 的只读取证（未成文）· [rpc-cluster-training-verdict] | pending | P1 | Step 1-2 完成：来源清单含 F1 日期 + F2 版本；外部引用 ≥3 条建 F4 表；断言逐条标 A/B/C |
| P-003 | 三站 RCCL 训练前置实测（跨机吞吐 / world_size=3 / A 站补装） | P-002 结论待定 | blocked | P2 | 三站在线后可做；当前 ping 全不通（2026-11-11 实测） |

## 依赖链

```
P-001（骨架）→ P-002（调研）→ P-003（实测）
```

## 档位声明

本仓批次档位判定沿用 `SPEC_PROCESS.md` §批次档位与裁剪理由：改动路径 ∩ {`scripts/`,`tests/`,`tools/`,`.pre-commit-config.yaml`,`.github/workflows/`} = ∅ → Layer-0 → T3；否则 T1。P-001 命中 `scripts/` + `.pre-commit-config.yaml` ⇒ **T1 完整管线**。
