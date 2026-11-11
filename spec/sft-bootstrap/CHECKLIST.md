# 审查验收 Checklist：sft-bootstrap（骨架自举）

---
id: sft-bootstrap-CHECKLIST
type: design
version: 1.0
status: accepting
date: 2026-11-11
depends: [sft-bootstrap-IMPLEMENTATION]
upstream: null
---

## 1. 文档一致性验收（Step 8）

### 1.1 RESEARCH ↔ DESIGN 对齐

| 调研结论 | 设计承接 | 判定 |
|---|---|---|
| §3.1 runner 两世代 | D3 选 v1.0.0 + 引用 | ✅ |
| §3.2 校验器绑上游形态 | D2 复制 + D6 pattern 重写 | ✅ |
| §3.3 hooks 实为 6 | D4 取 4 并登记缺口 | ✅ |
| §3.4 E 口径冲突 | 未进 DESIGN（落在 AGENTS.md） | ⚠ 部分——见 §8.2 发现 1 |

### 1.2 DESIGN ↔ IMPLEMENTATION 对齐

| 设计元素 | 实施位点 | 判定 |
|---|---|---|
| D1 宪法指针 | `AGENTS.md` 权威源指针表 | ✅ |
| D2 校验器副本 | `scripts/` 6 件 | ✅ |
| D3 runner 引用 + sessions 注入 | `spec_runner_adapter.py` `_exec()` env 注入 | ✅ |
| D4 4 hooks | `.pre-commit-config.yaml` 4 个 `- id:` | ✅ |
| D5 M7 独立计数 / DIS-100 | `docs/M7_EVIDENCE_LOG.md` §1 自 1 / `docs/discoveries/README.md` DIS-100 | ✅ |
| D6 pattern 只放真实措辞 | `CODE_WIKI §10` patterns 共 2 条 | ✅ |
| I-3 声明=重数 | `declared` 七键与机械重数一致 | ✅ |

### 1.3 IMPLEMENTATION ↔ CHECKLIST 对齐

| 实施项 | 验收项 | 判定 |
|---|---|---|
| §2.1 副本 | §2.1 | ✅ |
| §2.2 adapter | §2.2 | ✅ |
| §2.3 hooks | §2.3 | ✅ |
| §2.4 台账 | §2.4 | ✅ |
| §5 四缺口 | §8.2 / §10.3 | ✅ 全部如实携带，无一项被写成已解决 |

### 1.4 术语一致性

「E1-E5」在四文档与 `AGENTS.md` 均指**可重放性**分级；对 `D:\RPC` 的会话来源口径已就地标注区分。✅

## 2. 功能验收

### 2.1 校验器（DoD：命令 exit 0 且输出可读）

| 项 | DoR | 实测命令 | 读数 | 判定 |
|---|---|---|---|---|
| dc_validator | 本仓有 .md | `python scripts/dc_validator.py --check-all` | `14 文件，4 结果，0 违规` | ✅ |
| m7_stats | §5 有 hits 围栏 | `python scripts/m7_stats.py` | `0 结果，0 违规` | ✅ |
| repo_stats | CODE_WIKI 有 stats 块 | `python scripts/repo_stats.py` | `0 违规（P3 提示 0）` | ✅ |
| step_enforce | 需 HEAD 存在 | `python scripts/step_enforce.py` | `git error: invalid object name 'HEAD'` EXIT=2 | ❌ 未过（根因见 IMPL §5） |

### 2.2 runner 接入（DoD：事件入流 + replay 通过）

| 项 | 实测 | 判定 |
|---|---|---|
| `probe` | `gate[probe] verdict=pass exit=0` | ✅ |
| `gate dc-validator` | `verdict=pass exit=0`，事件 `stdout_tail` 含真实校验输出 | ✅ 非假绿 |
| `replay` × 2 session | `replay: 1 rows OK (seq monotonic, schema parseable)` | ✅ |
| sessions 落本仓 | `tools/spec_runner/sessions/` 两文件 | ✅ D3 达成 |

### 2.3 pre-commit（DoD：install 成功 + run --all-files 有判定）

| 项 | 实测 | 判定 |
|---|---|---|
| install | `pre-commit installed at .git\hooks\pre-commit` | ✅ |
| run --all-files | 3 Passed / 1 Failed（step-enforce） | ⚠ 部分 |

### 2.4 台账（DoD：校验器可对账）

| 项 | 判定 |
|---|---|
| PROGRESS 六列 + P-001~P-003 | ✅ |
| M7 §1/§2/§5 + hits 与机械重数一致 | ✅ |
| discoveries 五列 + DIS-100 含证据锚点 | ✅ |
| 三件均带 DC1 七字段 front-matter | ✅ |

## 3. 接口验收

| 接口 | 签名 | 回退点 | 判定 |
|---|---|---|---|
| adapter | `gates/probe/gate/run/status/replay/fork/dry-run` | 删文件即断流 | ✅ |
| `_exec()` | 注入 `SR_SESSIONS_DIR` | 删两行即回上游行为 | ✅ |

## 4. 不变式验收

| 不变式 | 取证 | 判定 |
|---|---|---|
| I-1 门禁真跑 | 事件流 `stdout_tail` 含校验器真实输出（E1） | ✅ |
| I-2 缺口如实登记 | `AGENTS.md` 已知缺口表 3 行 + IMPL §5 四行 | ✅ |
| I-3 声明=重数 | `repo_stats` 0 违规（E1） | ✅ |
| I-4 差异登记 | adapter docstring 差异节 + `M7_HITS_DESIGN.md` §1 | ✅ |

## 5. 错误处理验收

| 场景 | 期望 | 实测 | 判定 |
|---|---|---|---|
| hits 围栏缺失 | P1 阻断，不静默 | `[P1] hits 块缺失` EXIT=1 | ✅ |
| 声明与重数不符 | P1 报出实际值 | `声明 6 ≠ 机械重数 7` | ✅ |
| 空仓无 HEAD | 不崩，报 git error | `git error: ... EXIT=2` | ✅ 行为正确（非缺陷掩盖） |
| RUNNER 路径不存在 | 127 + 提示 | 未触发 | ❓ 未测 |

## 6. 性能验收

N/A——本批无性能判据（校验器为副本，未改算法）。

## 7. 兼容性验收

| 项 | 判定 |
|---|---|
| Windows 路径（反斜杠 / CRLF） | ✅ 校验器全跑通 |
| 中文文件名（ADR-0001） | ✅ git 与 dc_validator 均正常 |
| Python 3.13 | ✅ |

## 8. ADD 审计（Step 10）

### 8.1 Spec 质量门（Phase 0）

DESIGN 是否可审计：D1-D6 每条有理由与代价，I-1~I-4 有判据 ⇒ **通过**。

### 8.2 ADD 审计发现

| # | 阶段 | 发现 | 级别 | 位置 |
|---|---|---|---|---|
| 1 | Phase 2 忠实度 | RESEARCH §3.4 的 E 口径冲突未进 DESIGN 决策表，只在 `AGENTS.md` 落地——设计文档与实施面不完全对齐 | P3 | RESEARCH §3.4 / DESIGN 全文 |
| 2 | Phase 3 必要性 | **本条经自我更正**（原判断是形态 III 错误：证据真、推理跳步）。原判「`spec_map.py` 不在任何门禁 files 正则内 ⇒ 无设计依据的行为」——漏查了 `console_gen.py` L47 `import spec_map` 与 8 处调用。实测恢复后 `import console_gen` OK。更正后的真实缺口 = **`console_gen` + `spec_map` 是一对成对未接件**（D4 已登记 console-gen 不接，但未说明其依赖件同去同留） | P3 | `scripts/console_gen.py` L47 / L989 |
| 3 | Phase 1 完整性 | DESIGN D4 承诺"缺口如实登记"，但 `blackbox-tests` 未接一事在 `AGENTS.md` 有、在 PROGRESS 验收标准里无 ⇒ 台账与门面不一致 | P3 | `AGENTS.md` / `docs/PROGRESS.md` |
| 4 | Phase 4 语义 | 本批以「骨架完成」为目标，但 `step_enforce` 未过 ⇒ 严格说门禁是 **3/4** 而非 4/4；门面 `README.md` 写「四道」需在首提交后复核，否则机械合规而意图错位 | P2 | `README.md` 一屏表 |

### 8.3 ADD Iron Law 检查

「三校验器 exit 0」证明的是**校验器能跑**，不证明**骨架设计已落地**——后者由 §1-§4 逐项核对表承担，非由 exit code 代证。✅ 未以测试通过冒充设计落地。

## 9. 文档完整性

| 件 | 存在 | front-matter |
|---|---|---|
| RESEARCH / DESIGN / IMPLEMENTATION / CHECKLIST | ✅ | ✅ 七字段 |
| ADR-0001 | ✅ | ✅ |
| AGENTS / CODE_WIKI / README | ✅ | AGENTS/CODE_WIKI/README 无（DC1 判范围外 skip，与上游同形） |

## 10. 验收结论

### 10.1 验收统计

| 域 | 验收项 | 通过 | 未过 | 未测 |
|---|---|---|---|---|
| §1 一致性 | 4 | 3 | 1 | 0 |
| §2 功能 | 12 | 10 | 2 | 0 |
| §3 接口 | 2 | 2 | 0 | 0 |
| §4 不变式 | 4 | 4 | 0 | 0 |
| §5 错误处理 | 4 | 3 | 0 | 1 |
| §7 兼容性 | 3 | 3 | 0 | 0 |
| §9 文档 | 3 | 3 | 0 | 0 |
| 合计 | 32 | 28 | 3 | 1 |

（逐项核对表来源见 §1-§9 各行，非由总数推算——RULE-2）

### 10.2 验收决定

**有条件通过**。阻塞项 1 个：`step_enforce` 需首次 commit 才能出具判定。放行条件 = 首提交（`--no-verify` 一次，根因已查明为上游件对空仓的适配缺口）后复跑四道，若仍非全绿则回退本批。

### 10.3 签字

| 角色 | 主体 | RULE 标注 |
|---|---|---|
| 实施 | Claude Opus 5 | — |
| Review | 同一 agent | **自查（单视角）**（RULE-4）；RULE-5 异构审查**未执行**——出网第二视角待 P-002 一并接 |
| RULE-1 补 | — | **v1.0.0 取证降级**：无 `decision` 事件 / 无 `verify-anchor`，独立 pass 输入两项无法出具（见 IMPL §5） |
| 用户裁决 | Scott（鹏） | 档位 T1 / runner v1.0.0 / 指针载体 / 完全自举 |
