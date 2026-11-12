---
id: SFT-DISCOVERIES
type: process-spec
version: 1.0
status: active
date: 2026-11-11
depends: []
upstream: "F:\\Spec_Workflow\\docs\\discoveries\\README.md"
---

# Discoveries 发现日志（三态索引）

> **机制**: 沿用 `F:\Spec_Workflow\adr\ADR-0009-discoveries-log-mechanism.md`（本仓以指针引用，不复制）
> **集成点**: Step 2（调研异常记录发现）/ Step 10（ADD 审计系统性模式记录发现）
> **编号空间**: 本仓自 **DIS-100** 起——避开 Spec_Workflow（DIS-007~010）与 Cpp_Hub（DIS-001~006）两个已占区间

## 登记格式（五字段强制）

```markdown
| id | 状态 | 一句话 | 证据锚点 | 潜在论文? |
```

- **状态**（词表固定）: `open`（已识别裂缝未解决）/ `resolved`（已有反例+理论解释）/ `toolized`（方法论已落地为可执行工具）
- **证据锚点**: 事件现场/数据/修复记录的文件与位置（缺锚点不得登记）

## 索引

| id | 状态 | 一句话 | 证据锚点 | 潜在论文? |
|----|------|--------|---------|-----------|
| DIS-100 | open | **跨仓状态声明漂移**：下游仓 README 对上游仓「已冻结 / 已并入」的声明，与上游仓的实际活动状态可以长期不一致——声明是写入时点的快照，而 `git log` / `sessions/` 是活的；采信声明而不查活动痕迹，会把仍在服役的组件判成存档 | 2026-11-11 P-001 取证轮：`F:\Spec_Workflow\tools\spec_runner\README.md` 写「外仓 `F:\Spec_Runner` 冻结为历史存档」，实测该仓最后提交 2026-11-10 14:45、`sessions/` 含 factorv3 / finagent / oe / macrodata / myproj / specwf 六个前缀的事件流；同轮据此误判差点选错 runner 版本（后由 `git log` + `grep add_parser` 双查纠正） | 是（分布式系统的元数据陈旧问题在「文档即状态」场景的复现） |
| DIS-101 | open | **上游门禁件的隐式自举假设**：校验器把「本仓 session 前缀」和「runner 会产 `decision` 事件」当作普适事实硬编码，跨仓沿用时不是报错而是**恒不匹配**——表现为「P 行无 session」，与"真的没建 session"两种状态读起来一模一样 | 2026-11-12 P-002 Step 2 后：`step_enforce.py` L129 `SESSIONS.glob(f"specwf-{key}-*.jsonl")` 硬编码 `specwf-`，本仓前缀实测为 `sft`（`ls tools/spec_runner/sessions/` 单一前缀）⇒ 无论建多少 session 都匹配不到；L195 又要求 `event=="decision"`，而 `F:\Spec_Runner` v1.0.0 命令面 grep `decision` = 0 命中。同族先例 = `console_gen.py` L186 `glob("specwf-p*.jsonl")`（P-001 已登记未接）。**为何是发现而非 bug**：判据本身正确，错在把环境态写成了常量——与 SPEC_PROCESS v1.6 通则 4「skill 是环境态，不得让环境态成为流程依赖」同构，但该校验器自身违反了这条 | 是（可复用工具链中"隐式环境假设"的失效形态与检测法） |
| DIS-102 | open | **锚点语法不接受非 ASCII 文件名**：`verify-anchor` 的锚点正则把路径段限定为 `[A-Za-z0-9_./-]+`，中文文件名一律判「形态不可解析」⇒ 在**以中文命名文档的仓**里，这些文档永远无法作为 evidence 锚点被机检 | 2026-11-12 P-004 实施轮：`tools/spec_runner/spec_runner.py` L391/L395 两条 `re.match` 的字符类均无 Unicode 区间；实测 `adr/ADR-0001-spec-carrier-pointer-not-copy.md#L49` 判 HARD，而同一形态的 `docs/PROGRESS.md#L18` 判真实 ⇒ 差异仅在文件名字符集。本仓绕行 = 决策链改指 `spec/sft-bootstrap/DESIGN.md#L24`（同一裁决的 ASCII 名落点），并在 decisions.json 内以 `note` 留原锚。**【P-011 处置更新】绕行并未治本**——写 ADR-0002 时又撞上（`§决策` 非数字章节 + 中文文件名**双重**不可解析），5 条锚点全判 HARD。★ 已改**命名策略**治本：本仓 ADR 文件名一律 ASCII（`ADR-0001-spec-carrier-pointer-not-copy.md` / `ADR-0002-degradation-gate.md`），中文标题留在文件内，全仓 8 个文件的引用同步改写 ⇒ 状态 open → **resolved**（策略层规避，工具本身未改）。**为何是发现而非 bug**：ASCII 白名单是有意的严格形态约束，错在跨仓沿用时未声明该前提——与 DIS-101 同族，但本条影响**命名策略**而非判据匹配，凡中文命名文档的下游仓都会撞上 | 是（工具形态约束与人类可读命名的张力，及机检覆盖率损失） |

## 统计

- 本仓发现数: 3（DIS-100 open / DIS-101 open / DIS-102 **resolved**）——由 `grep -c "^| DIS-" docs/discoveries/README.md` 机械重数，非手填
