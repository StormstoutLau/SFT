# DEV-LOG-001 — sft-bootstrap 骨架自举

> **日期**: 2026-11-11 · **批次**: P-001 · **档位**: T1
> **执行**: Claude Opus 5 · **裁决**: Scott（鹏）

## 做了什么

把 `D:\SFT` 从空目录建成可跑门禁的自举骨架：

1. 目录树 + 三台账（PROGRESS / M7 / discoveries）+ ADR-0001
2. 复制上游 6 件校验器 + 6 份模板（ADR-0001 决策 2）
3. 新写 `scripts/spec_runner_adapter.py`，接 `F:\Spec_Runner` v1.0.0，`SR_SESSIONS_DIR` 注入回本仓
4. `.pre-commit-config.yaml` 四道 hook，已 install
5. 四文档管道（RESEARCH / DESIGN / IMPLEMENTATION / CHECKLIST）回溯落档

## 决策依据

见 `adr/ADR-0001-规范载体为指针而非副本.md` 与 `spec/sft-bootstrap/DESIGN.md` D1-D6。

## 遇到的问题（含自身错误）

| # | 问题 | 根因 | 处置 |
|---|---|---|---|
| 1 | 误判 `F:\Spec_Runner` 已冻结 | 采信上游 README 声明，未查外仓 `git log` | 实测推翻后改写；入 M7 样本 1（形态 II 版本号）+ DIS-100 |
| 2 | 误判 `spec_map.py` 无消费者并删除 | 只查 pre-commit 的 files 正则，漏查 `console_gen.py` L47 `import spec_map` | 恢复；入 M7 样本 2（**形态 III**——证据真、推理跳步） |
| 3 | `m7_stats --write` 拒绝 bootstrap | 该命令只重写已有 `hits` 围栏，不创建 | 手建围栏后 `--write` 正常 |
| 4 | `step_enforce` exit 2 | `_local_changed()` 依赖 `HEAD`，空仓无首次提交 | 未修（属上游件对首提交的适配缺口）；首提交需 `--no-verify` 一次 |
| 5 | `repo_stats` 两次抓到我 | 加 adapter / 加 feature 目录后未同步 `declared` | 改 7 / 改 2——**门禁按设计生效**，非误报 |

## 门禁读数（E1，可重放）

```
DC contract validator (DC1-DC5 + R7)................Passed
M7 ledger hits block validator......................Passed
View-layer enumeration validator (stats block)......Passed
Step decision-stream enforcement....................Failed (exit 2, 空仓 HEAD)
gate[dc-validator] verdict=pass exit=0            # 事件流入 tools/spec_runner/sessions/
replay: 1 rows OK (seq monotonic, schema parseable)
```

## 下一步

- P-002：分布式微调正式调研（`spec/distributed-sft/RESEARCH.md`），按 F1-F5 出具
- RULE-5 异构审查：接出网 API 的不同模型家族做第二视角（本批全部标注为「自查（单视角）」）
- 首提交后复核 step-enforce，若仍非全绿则回退本批（CHECKLIST §10.2）
