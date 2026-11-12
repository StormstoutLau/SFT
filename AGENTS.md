# AGENTS.md

> **本文件 = `F:\Spec_Workflow\SPEC_PROCESS.md` 的操作摘要桥**（沿用其 CER C-01 形态）。
> **权威源**：`F:\Spec_Workflow\SPEC_PROCESS.md` v1.7.2 —— 本文件保持「指针 + 最小摘要」，**不复制规则全文**；如有出入以权威源为准。载体裁决见 [ADR-0001](adr/ADR-0001-spec-carrier-pointer-not-copy.md)。

## 仓库性质

分布式微调工作区。产出 = spec 四文档 + 实测脚本 + 证据账本；**本仓不含训练引擎**，算力底座是 `D:\RPC` 三机集群。

## 开发流程

每个 feature 产出 `RESEARCH → DESIGN → IMPLEMENTATION → CHECKLIST` 四文档管道，偶数步为 Review 门禁。批次档位判定（T1 完整管线 / T3 轻批）见权威源 §批次档位与裁剪理由：**改动路径 ∩ {`scripts/`,`tests/`,`tools/`,`.pre-commit-config.yaml`} = ∅ → Layer-0 → T3；否则 T1**。

## 校验命令

修改任何文档后、提交前（pre-commit 已配，提交时自动执行）：

```bash
python scripts/dc_validator.py --check-all   # DC1-DC5 契约 + 机械重数
python scripts/m7_stats.py                   # M7 hits 块对账（重生成用 --write）
python scripts/repo_stats.py                 # 视图层声明 = 机械重数
python scripts/step_enforce.py               # 批次 session 存在性
python scripts/spec_runner_adapter.py probe  # runner 接入自检（事件入流）
```

## 证据口径（本仓沿用 Spec_Workflow，按**可重放性**分级）

| 级 | 含义 | 附加约束 |
|---|---|---|
| E1 | 可重放命令 | — |
| E2 | 运行时脚本取证 | 须附场景选择理由或含对抗性场景 |
| E3 | 静态读码行号 | **强制绑 commit hash**（`L124@<hash>`） |
| E4 | 盲区扫描 / 判断 | 须以「发现 N 项」语气，禁止裸 ✅ |
| E5 | 推测 | **禁止出现在审计结论**，只能进「未覆盖项」 |

⚠ **跨仓口径冲突**：`D:\RPC` 的 `E1-E4` 按**会话来源**分级（E1=本会话实测 / E3=外部文档），与上表语义不同。读到别处的 `E3` 先确认是哪一套。

## 禁止事项

- 不得跳过 pre-commit 检查
- 不得手改 M7 的 hits 统计声明（由 `m7_stats.py --write` 机械重写）
- 破坏性文件操作（覆盖 / 截断 / 批量替换）前必须备份
- 文档中的计数声明必须与机械重数一致
- **同一文件的多个修改必须严格串行**（前一 Edit 结果返回确认后再发下一 Edit；DIS-008——并行 Edit 会以陈旧快照覆盖先发编辑，产生静默回滚）；不同文件可并行
- **batch 编辑后必须对全部修改行做全覆盖终验 grep**（不得抽样），再运行校验器
- **制品状态变更必须同步 front-matter**（`id`/`type`/`version`/`status`/`date`/`depends`/`upstream` 七字段），且与 `CODE_WIKI §9` 索引行、`PROGRESS` 行一致
- 正文/表格中不得直接书写「`]` 紧跟 `(`」相邻的字面量（`dc_validator` M5 不做 markdown 语义解析，会误判为相对链接不可解析）

## 本仓已知缺口（如实登记，不得声称已满足）

| 缺口 | 影响 | 出处 |
|---|---|---|
| ~~runner v1.0.0 能力缺口~~ **已消**（P-004 升级至 v1.11.0 并复制进本仓） | `decision` / `verify-anchor` / `step-gate` 现可用 ⇒ RULE-1 补的取证**可完整出具**；本仓不再标「v1.0.0 取证降级」 | E1：`tools/spec_runner/spec_runner.py --version` = 1.11.0 |
| **锚点语法不接受非 ASCII 文件名** | 中文命名的文档（如本仓 ADR）**无法作为 evidence 锚点被机检**，决策链须改指 ASCII 名文件 | E3：`spec_runner.py` L391/L395 字符类；DIS-102 |
| `console_gen` / `blackbox-tests` 未接 | 本仓 hooks = 4 而非上游 6；`console_gen` 硬编码 `specwf-p*.jsonl` 前缀（6 处），改前方可接 | DIS-101 同族 |
| 三站离线 | 一切训练相关实测标 `blocked`，不预写结论 | E1：2026-11-11 ping 全不通 |

## 权威源指针

| 主题 | 权威源（`F:\Spec_Workflow\`） |
|------|--------|
| 流程宪法（10 步 + Review 规则） | `SPEC_PROCESS.md` |
| 断言分级框架（A/B/C + E1-E5） | `docs/ASSERTION_EVIDENCE_FRAMEWORK.md` |
| 决策记录契约 | `docs/DECISION_RECORD_CONTRACT.md` |
| 四文档模板 | `spec/templates/`（本仓有副本，可本地改） |
| runner 设计规格 | `spec/spec-runner/SPEC_RUNNER_DESIGN.md` |
