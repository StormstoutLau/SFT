# 调研文档：sft-bootstrap（骨架自举）

---
id: sft-bootstrap-RESEARCH
type: design
version: 1.0
status: draft
date: 2026-11-11
depends: []
upstream: null
---

> **批次**: P-001 · **档位**: T1（命中 `scripts/` + `.pre-commit-config.yaml` ⇒ Layer-1）
> **诚实声明**: 本批是**实施先于文档**的回溯落档——用户 2026-11-11 直接指令「先建骨架」，四文档在实施后补齐。按 ADD Iron Law 如实登记，不假装 Step 1 先于 Step 9。

## 1. 调研目标

把 `F:\Spec_Workflow`（方法论权威源）+ `F:\Spec_Runner`（门禁执行器）在空目录 `D:\SFT` 落成可跑的工作区骨架，并确定沿用边界。

## 2. 调研方法

### 2.1 使用的工具

| 通道 | 用途 | Layer |
|---|---|---|
| `Bash` / `grep` / `sed` | 读上游规范与校验器源码 | T1 一手（仓内文件） |
| `git log` / `ls` | 核上游仓的实际活动状态 | T1 |
| `python scripts/*.py` | 实跑校验器取判据 | T1（E1） |

### 2.2 调研范围

`F:\Spec_Workflow`（SPEC_PROCESS v1.7.2 / 三校验器 / M7 / PROGRESS / CODE_WIKI / pre-commit）、`F:\Spec_Runner`（v1.0.0）、`D:\RPC`（算力底座，见 [[rpc-cluster-training-verdict]]）。

## 3. 调研发现

### 3.1 上游 runner 存在两份，语义不同（★ 本批最重要发现）

| 断言 | 级 | 证据 |
|---|---|---|
| `F:\Spec_Runner\spec_runner.py` 是 **v1.0.0**，命令面仅 `run/gate/status/replay/fork/selftest` | A | E3：`spec_runner.py` L25 `VERSION = "1.0.0"` + L313-342 `add_parser` 六项；`grep -c decision` = **0** |
| `F:\Spec_Workflow\tools\spec_runner\spec_runner.py` 是 **v1.11.0**，另有 `step-gate` / `verify-anchor` / `decision` 事件 / fork 返工图 | A | E3：L27 `VERSION = "1.11.0"`；`tools/spec_runner/README.md` 命令面节 |
| 外仓**并未冻结**（上游 README 声称已冻结） | B | 推理链：① `tools/spec_runner/README.md` 写「外仓冻结为历史存档」→ ② 实测 `git log -1` = **2026-11-10 14:45** → ③ `sessions/` 含 factorv3 / finagent / oe / macrodata / myproj / specwf 六前缀 → ④ 结论：声明陈旧，外仓实为**跨项目共享 runner** |
| v1.0.0 无法出具 RULE-1 补要求的取证 | B | 推理链：① RULE-1 补要求输入 = 含 `decision` 的事件流 + `verify-anchor` 输出（SPEC_PROCESS L236-242）→ ② v1.0.0 两者皆零命中（E3 见上）→ ③ 故本仓该条**只能降级出具** |

### 3.2 校验器绑死上游自举形态

| 断言 | 级 | 证据 |
|---|---|---|
| `dc_validator.py` 的 `ROOT` 由 `__file__` 派生 ⇒ 复制即换根 | A | E3：L29 `ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))` |
| `console_gen.py` 硬编码 `tools/spec_runner/sessions` + glob `specwf-p*.jsonl` ⇒ 看不到本仓 `sft-` 前缀 session | A | E3：L50-52 常量 + L186 `glob("specwf-p*.jsonl")` |
| `m7_stats.py --write` 不创建 `hits` 围栏，仅在已存在时重写 | A | E1：首次 `--write --seed-pre-ledger 0` 报 `[P1] 存在 §5 节却无 hits 围栏——须人工修复后重试` |
| `repo_stats.py` 的 pattern 库绑上游中文措辞（`PT-1` 匹配「形态 II …N 处」等） | A | E3：`TRUTH_KEYS` 封闭枚举 L64-72 + 上游 `CODE_WIKI` stats 块 20 条 pattern |

### 3.3 pre-commit 实际是 6 道而非 3 道

| 断言 | 级 | 证据 |
|---|---|---|
| 上游 hook 数 = **6**（dc-validator / m7-stats / repo-stats / step-enforce / console-gen / blackbox-tests），`AGENTS.md` 只列前三 | A | E3：`.pre-commit-config.yaml` 六个 `- id:`；`AGENTS.md` 校验命令节仅三行 |
| 本仓首建为 **4** 道（未接 console-gen / blackbox-tests） | C | rationale：`console_gen` 需改常量、`tests/` 尚空 ⇒ 先接可跑的四道，缺口如实登记不谎称全绿 |

### 3.4 跨仓证据等级口径冲突

| 断言 | 级 | 证据 |
|---|---|---|
| Spec_Workflow 的 E1-E5 按**可重放性**；`D:\RPC` 的 E1-E4 按**会话来源**，同一标记两套语义 | A | E3：`SPEC_PROCESS.md` L385-391 五分类表 vs `D:\RPC\adr\ADR-0013-*.md`「E1=本会话实测；E3=外部文档」 |

## 4. 综合分析

### 4.1 关键发现总结

上游不是单一权威源，而是**两份不同世代的 runner + 一套绑死自举形态的校验器**。沿用必须先选边，否则会在"声称遵守 RULE-1"的同时物理上无法出具其取证。

### 4.2 技术 landscape

三选一：外仓 v1.0.0（照 factorv3 先例）/ 复制 v1.11.0（第三副本）/ 跨仓引用 v1.11.0（硬耦合）。用户裁 **v1.0.0**。

### 4.3 研究空白

本仓尚无 `tests/`，`blackbox-tests` 那道门禁（上游 15 用例）未接 ⇒ 校验器自身行为在本仓无回归保护。

## 5. 幻觉抑制审查（Step 2 Review）

### 5.1 文献验证

本批**无外部文献引用**（全部为仓内文件取证）⇒ F4 引用验证表 **N/A**，理由：F4 仅在存在外部引用时触发。

### 5.2 技术声明验证

| 声明 | 验证方式 | 状态 |
|---|---|---|
| v1.0.0 无 decision | `grep -c decision` = 0 | 已验证（E3） |
| 外仓未冻结 | `git log -1` 读数 | 已验证（E1） |
| dc_validator 跨仓可跑 | 本仓实跑 exit 0 | 已验证（E1） |
| hooks 机械重数 = 4 | `repo_stats` 报「声明 0 ≠ 机械重数 4」 | 已验证（E1） |

### 5.3 待修正项

**自查（单视角）**（RULE-4）：本批由同一 agent 既实施又撰写文档，无对抗性。§3.1 首版结论曾为「外仓已冻结」，被 `git log` 实测推翻后改写——该错误已入 [M7 样本 1](../../docs/M7_EVIDENCE_LOG.md) 与 [DIS-100](../../docs/discoveries/README.md)。

## 6. 对设计的输入

### 6.1 可用的技术方案

见 §3.2 各条 ⇒ 落点：复制校验器、注入 `SR_SESSIONS_DIR`、pattern 库重写、hooks 取 4。

### 6.2 关键约束

`m7_stats --write` 需已有围栏（须手建 §5 骨架）；`step_enforce` 需 HEAD 存在。

### 6.3 风险

副本漂移：本仓校验器与上游从此独立演化，无同步门禁。

### 6.4 未决项登记（四元块）

| 判据 | 触发条件 | 当前倾向 | 证据等级 |
|---|---|---|---|
| 是否改用 v1.11.0 以补 RULE-1 补取证 | 出现首个需要 `decision` 链的独立 pass 批次 | 不改——先如实标降级，等真需要时再裁 | E4 |
| `step_enforce` 空仓缺口怎么修 | 首次 commit 时 | 首提交 `--no-verify` 一次并登记，不改上游件 | E1 |
| 是否接 console-gen | 本仓 P 行 > 10 且需要派生视图时 | 推迟 | E4 |

## 7. 参考文献

无外部文献。仓内取证位点：`F:\Spec_Workflow\SPEC_PROCESS.md` v1.7.2 · `docs/ASSERTION_EVIDENCE_FRAMEWORK.md` v1.4.2 · `.pre-commit-config.yaml` · `scripts/{dc_validator,m7_stats,repo_stats,step_enforce,console_gen}.py` · `F:\Spec_Runner\spec_runner.py` v1.0.0 · `D:\RPC\docs\research\2026-09-30_RCCL部署方案与集群必要性评估.md`。
