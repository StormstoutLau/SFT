# D:\SFT —— 分布式微调工作区

> 规范权威源 = `F:\Spec_Workflow`（本仓以指针沿用，见 [ADR-0001](adr/ADR-0001-规范载体为指针而非副本.md)）
> 算力底座 = `D:\RPC` 三机集群
> 门面状态：骨架自举中（P-001）

## 一屏

| 项 | 值 |
|---|---|
| 定位 | 在 3× Strix Halo（128 GB UMA）+ USB4 环上做分布式微调的调研与设计工作区 |
| 规范 | Spec 驱动 10 步流程 + RULE-1~6 + 断言 A/B/C + 证据 E1-E5 |
| 门禁 | `pre-commit` 四道（dc-validator / m7-stats / repo-stats / step-enforce） |
| 执行器 | `F:\Spec_Runner` v1.0.0（事件流落 `tools/spec_runner/sessions/`） |
| 台账 | `docs/PROGRESS.md`（待办）· `docs/M7_EVIDENCE_LOG.md`（证据）· `docs/discoveries/`（发现） |

## 快速开始

```powershell
# 门禁全量
python scripts\dc_validator.py --check-all
python scripts\m7_stats.py
python scripts\repo_stats.py
python scripts\step_enforce.py

# runner 接入自检（事件入流）
python scripts\spec_runner_adapter.py probe
python scripts\spec_runner_adapter.py replay
```

## 目录

| 路径 | 内容 |
|---|---|
| `adr/` | 架构决策记录（编号空间独立，见 ADR-0001） |
| `docs/` | 三台账：PROGRESS / M7 / discoveries |
| `scripts/` | 校验器（上游副本）+ runner adapter |
| `spec/` | 四文档管道（`templates/` + 各 feature） |
| `tools/spec_runner/sessions/` | Spec_Runner 事件流（append-only JSONL） |

## 已知边界（如实）

- **三站当前离线**：训练相关实测全部标 `blocked`，不预写结论。
- **runner v1.0.0 能力缺口**：无 `decision` 事件与 `verify-anchor` ⇒ RULE-1 补的独立 pass 取证在本仓降级出具，每轮如实标注。
- **`console_gen` / `blackbox-tests` 未接**：上游件硬编码 `specwf-p*.jsonl` 前缀与 `tools/spec_runner/sessions/` 路径，本仓 session 前缀为 `sft-`，须改常量后再接。
