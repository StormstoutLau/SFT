# 实施文档：sft-bootstrap（骨架自举）

---
id: sft-bootstrap-IMPLEMENTATION
type: design
version: 1.0
status: draft
date: 2026-11-11
depends: [sft-bootstrap-DESIGN]
upstream: null
---

## 1. 环境与依赖核验（Step 6 Review 输入）

| 件 | 版本 | 核验方式 | 状态 |
|---|---|---|---|
| Python | 3.13.5 | `python --version` | 已验证（E1） |
| git | 2.53.0.windows.2 | `git --version` | 已验证（E1） |
| pre-commit | 4.7.0 | `pip list` | 已验证（E1） |
| pytest / mypy / black | 8.3.4 / 1.14.1 / 24.10.0 | `pip list` | 已验证（E1，本批未用） |
| `F:\Spec_Runner\spec_runner.py` | **1.0.0** | E3：文件 L25 `VERSION` | 已验证 |
| `F:\Spec_Workflow\SPEC_PROCESS.md` | 1.7.2 | front-matter `version` | 已验证 |
| `F:\Spec_Workflow\docs\ASSERTION_EVIDENCE_FRAMEWORK.md` | 1.4.2 | front-matter `version` | 已验证 |

## 2. 落地面与接口

### 2.1 校验器副本（6 件，未改语义）

`scripts/{dc_validator,m7_stats,repo_stats,step_enforce,console_gen,spec_map}.py` ← 上游同名文件逐字节复制。回退点：删除 `scripts/` 即回到空仓，无残留状态。

⚠ `console_gen.py` / `spec_map.py` 本批**未接入** pre-commit（D4），存在但不跑。

### 2.2 `scripts/spec_runner_adapter.py`（本仓新写）

签名：`gates | probe | gate <name> [--session S] | run --task T [--require-gate G] | status | replay | fork | dry-run`

与上游模板的**唯一**差异（I-4 登记）：`_exec()` 增 `env = dict(os.environ, SR_SESSIONS_DIR=SESSIONS)` 与 `mkdir`。不改 gate 语义、不复制 runner 逻辑。

回退点：删本文件即断开门禁入流，四校验器仍可手工跑。

### 2.3 `.pre-commit-config.yaml`（4 hooks）

| hook | entry | files 判据 |
|---|---|---|
| dc-validator | `python scripts/dc_validator.py` | `^(?!.*\.arc/).*\.md$` |
| m7-stats | `python scripts/m7_stats.py` | `^docs/M7_EVIDENCE_LOG\.md$` |
| repo-stats | `python scripts/repo_stats.py` | `^(CODE_WIKI\.md|README(\.en)?\.md|\.pre-commit-config\.yaml|docs/|spec/|adr/|scripts/)` |
| step-enforce | `python scripts/step_enforce.py` | 四文档 + `tools/spec_runner/sessions/.*\.jsonl` + `docs/PROGRESS.md` |

回退点：`pre-commit uninstall` 移除钩子，`.git/hooks/` 复原。

### 2.4 台账三件

`docs/PROGRESS.md`（六列，P-001~P-003）· `docs/M7_EVIDENCE_LOG.md`（§1/§2/§5 + hits 块）· `docs/discoveries/README.md`（五列，DIS-100）。

## 3. 红→绿记录（F5）

| # | 红 | 绿 |
|---|---|---|
| 1 | `m7_stats`：`[P1] hits 块缺失`，EXIT=1 | `M7 统计校验通过：0 结果，0 违规`，EXIT=0 |
| 2 | `m7_stats --write`：`[P1] 存在 §5 节却无 hits 围栏——须人工修复后重试` | 手建围栏后 `--write` 不再需要，verify 直过 |
| 3 | `repo_stats`：`declared.hooks 声明 0 ≠ 机械重数 4` | 改 4 → 通过 |
| 4 | `repo_stats`：`declared.scripts 声明 6 ≠ 机械重数 7`（加 adapter 后未同步视图） | 改 7 → `视图层对账通过：0 违规` |
| 5 | `step_enforce`：`git error: fatal: invalid object name 'HEAD'`，EXIT=2 | **未转绿**——空仓无首次 commit，见 §5 |

## 4. 低效操作排除表

| 排除项 | 理由 |
|---|---|
| 不照抄上游 20 条 pattern | 匹配不到本仓文本 = 恒真门禁 |
| 不复制 SPEC_PROCESS 全文 | D1；601 行副本无同步门禁 |
| 不建 `README.en.md` | 上游 facade 需要它只因有英文版；本仓无 |
| 不接 `deepeval_m7_eval.py` / `pf_m7_eval.py` | 需 promptfoo/deepeval 外部服务，本批无对象 |

## 5. 已知缺口（不得声称已解决）

| 缺口 | 根因 | 处置 |
|---|---|---|
| `step_enforce` 空仓 exit 2 | `_local_changed()` 依赖 `HEAD`，首次提交前不存在 | 首提交 `--no-verify` 一次；此后正常。**不改上游件** |
| RULE-1 补取证缺失 | runner v1.0.0 无 `decision` / `verify-anchor` | 每个 Review 轮标「v1.0.0 取证降级」 |
| `console_gen` 看不到本仓 session | 硬编码 `specwf-p*.jsonl` | 未接，已登记 D4 |
| `tests/` 空 | 本批无被测新代码（adapter 是薄壳） | P-002 起按需补 |
