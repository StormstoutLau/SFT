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

## 统计

- 本仓发现数: 1（DIS-100 open）——由 `grep -c "^| DIS-" docs/discoveries/README.md` 机械重数，非手填
