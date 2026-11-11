# CODE_WIKI —— D:\SFT 知识库索引

> **仓库性质**: 分布式微调工作区（算力底座 = `D:\RPC` 三机集群）
> **规范权威源**: `F:\Spec_Workflow\SPEC_PROCESS.md`（本仓以指针沿用，见 [ADR-0001](./adr/ADR-0001-规范载体为指针而非副本.md)）
> **建立**: 2026-11-11

## 1. 项目概览

### 1.1 定位

在 `D:\RPC` 三机集群（AMD Ryzen AI Max+ 395 ×3 / 128 GB UMA / USB4 三角环）上做分布式微调的**调研—设计—实施**工作区。本仓自身不含训练引擎，产出是 spec 文档 + 实测脚本 + 证据账本。

### 1.2 解决的问题

`D:\RPC` 是推理集群、零训练代码，但其 RCCL 跨机 `all_reduce` 已实测跑通（182 µs）。本仓回答：这套底座能支撑哪种形态的分布式训练，代价是什么。

## 2. 物理目录结构

```
D:\SFT\
├── AGENTS.md              规范摘要桥（指针）
├── CODE_WIKI.md           本文件
├── README.md              门面
├── .pre-commit-config.yaml 门禁
├── adr/                   架构决策记录
├── docs/
│   ├── PROGRESS.md        待办台账（真值源）
│   ├── M7_EVIDENCE_LOG.md 证据账本（真值源）
│   ├── CONSOLE.md         派生视图（机器生成）
│   ├── discoveries/       发现日志（三态索引）
│   └── dev-log/           开发日志
├── scripts/               校验器（副本，见 ADR-0001 决策 2）
├── spec/
    ├── m7-hits-block/     M7 hits 块本仓差异说明
    ├── sft-bootstrap/     P-001 四文档管道
    └── templates/         四文档模板（副本）
├── tests/
└── tools/spec_runner/sessions/   Spec_Runner 事件流（runner 本体在 F:\Spec_Runner）
```

## 3. 关键约束（本仓特有）

| 约束 | 内容 | 证据 |
|---|---|---|
| 算力前置 | 三站 2026-11-11 全部离线（ping 不通），训练实测须等上线 | E1 |
| 互联硬顶 | USB4 实测 9.0~9.46 Gb/s ≈ 1.1 GB/s，无 RDMA | E2（`D:\RPC` 留档） |
| runner 能力缺口 | `F:\Spec_Runner` v1.0.0 无 `decision` / `verify-anchor` ⇒ RULE-1 补的两项取证在本仓**标降级出具** | E3 |

## 9. 文档索引

| 文档 | 版本 | 状态 | 说明 |
|---|---|---|---|
| [ADR-0001](./adr/ADR-0001-规范载体为指针而非副本.md) | v1.0 | accepted | 规范载体三分：宪法指针 / 可执行件副本 / 差异就地登记 |
| [m7-hits-block](./spec/m7-hits-block/) | v1.0 | draft | M7 hits 块本仓差异说明 |
| [sft-bootstrap](./spec/sft-bootstrap/) | v1.0 | accepting | P-001 骨架自举四文档 |
| [PROGRESS](./docs/PROGRESS.md) | v1.0 | active | 待办台账 |
| [M7](./docs/M7_EVIDENCE_LOG.md) | v1.0 | active | 证据账本 |
| [discoveries](./docs/discoveries/README.md) | v1.0 | active | 发现日志（DIS-100 起） |

## 10. 机读统计块（stats）

> 视图层声明的唯一登记处（R7 同构：声明 = 机械重数）。对账器 = `scripts/repo_stats.py`（只读，无 `--write`）。

```stats
{
  "pattern_lib_version": 1,
  "carriers": {
    "living": ["CODE_WIKI.md", "docs/discoveries/README.md", "docs/PROGRESS.md"],
    "facade": ["README.md"]
  },
  "patterns": [
    {"id": "PT-11", "regex": "P-(\\d{3})~P-(\\d{3})", "truth": "fs.progress_tasks", "group": 2},
    {"id": "PT-6B", "regex": "架构决策记录（([一二三四五六七八九十\\d]+)份", "truth": "fs.adr_files", "scope": ["CODE_WIKI.md"]}
  ],
  "declared": {
    "spec_feature_dirs": 2,
    "adr_files": 1,
    "dev_logs": 1,
    "scripts": 7,
    "templates": 6,
    "hooks": 4,
    "progress_tasks": 3
  },
  "view_layer_samples": [],
  "doc_registry": [
    {"label": "ADR-0001", "path": "adr/ADR-0001-规范载体为指针而非副本.md"},
    {"label": "PROGRESS", "path": "docs/PROGRESS.md"},
    {"label": "M7", "path": "docs/M7_EVIDENCE_LOG.md"},
    {"label": "discoveries", "path": "docs/discoveries/README.md"},
    {"label": "m7-hits-block", "path": "spec/m7-hits-block/M7_HITS_DESIGN.md"}
  ]
}
```
