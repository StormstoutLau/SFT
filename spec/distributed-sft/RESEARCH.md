# 调研文档：distributed-sft（分布式微调可行性与方案）

---
id: distributed-sft-RESEARCH
type: design
version: 1.1
status: draft
date: 2026-11-12
depends: [sft-bootstrap-RESEARCH]
upstream: null
---

> **批次**: P-002 · **档位**: T1（产出四文档 + 后续动 `scripts/`）
> **取证口径**: 本仓沿用 Spec_Workflow 的**可重放性**分级（E1-E5），非 `D:\RPC` 的会话来源口径。跨仓读数已逐条注明来源仓。

## 1. 调研目标

回答两问：① `D:\RPC` 三机集群能支撑哪种形态的分布式微调；② 针对已识别瓶颈，社区有无可用方案。

## 2. 调研方法

### 2.1 使用的工具与降级链（F3）

| 目标通道 | 状态 | 实际通道 | 读到的事实 / 未取证 |
|---|---|---|---|
| `mcp_english-search.search_web` | ❌ **HTTP 522 × 3**（Cloudflare 源站不可达） | `mcp_paper-search.search_arxiv` | 18 条 T1 学术源（见 §7）；**社区实测层未取证** |
| `WebFetch` → `docs.unsloth.ai` | ❌ 域名安全校验失败（网络策略） | `D:\RPC` 仓内二手记录 | Unsloth 官方加速数据**未回原文**，全部标 E3 转述 |
| `WebFetch` → `github.com/ROCm/ROCm/issues` | ❌ 分类器瞬时拒绝，未重试成功 | — | **gfx1151 训练相关 issue 现状未取证** |
| `mcp_stackexchange.search_questions` | ✅ 可用 | 同 | `stackoverflow` 查 `ROCm Strix Halo PyTorch training gfx1151` = **0 命中**；`askubuntu` 查 `Ryzen AI Max 395 Strix Halo machine learning training` = **0 命中** |
| `Bash` / `git` / `grep`（本仓 + `D:\RPC`） | ✅ | 同 | 底座全部事实（E1/E3） |

⚠ **降级链的诚实含义**：本批**没有**拿到任何第三方社区实测（T3 层）。§3.4 把这条列为研究空白而非"搜索失败"。

### 2.2 调研范围

`D:\RPC@3126626`（2026-11-04）四份取证文档 + arXiv 18 篇 + 本仓 P-001 已确立的传输/门禁事实。

## 3. 调研发现

### 3.1 底座事实（全部来自 `D:\RPC@3126626`，E3 绑 blob hash）

| # | 断言 | 级 | 证据 |
|---|---|---|---|
| B1 | PyTorch **2.12.0+rocm7.15.0** 在 B 站 venv 实跑，`DEV_ARCH gfx1151` | A | E3：`docs/research/2026-09-30_RCCL…md` L160-166@`639370515b50`（含 `TORCH 2.12.0+rocm7.15.0a20260724` 逐字读数） |
| B2 | **RCCL 2.30.4 内建 gfx1151 目标** + 官方 `rccl_lib_gfx1151.kpack`（19.6 MB）⇒ 旧"需社区补丁"结论过期 | A | E3：同上 L146-152@`639370515b50` |
| B3 | ★ 跨机 `all_reduce` **实测跑通**：B↔C，纯 `torch.distributed` + 2 SSH 进程，9 channel 全建，median **182.0 / 181.2 µs**，`sum=98304.0` 正确性通过 | A | E3：同上 L188-205@`639370515b50` |
| B4 | 必须用 `NCCL_SOCKET_IFNAME`；`RCCL_SOCKET_IFNAME` 在 librccl 中**不存在**，设了静默挂死 | A | E3：同上 L179-186@`639370515b50` |
| B5 | 互联：USB4 协商 **20 Gb/s**（Gen3x2 训练失败降级），iperf3 实测 **9.0~9.46 Gb/s**，MTU 9000 | A | E3：`docs/2026-09-15_B站USB4无连接排查与归档.md` L153 + `spec/rpc-optimization/USB4-40G链路能力评估.md` §4.1 |
| B6 | **无 RDMA**：三站 `/sys/class/infiniband/` 全空，RCCL 报 `NET/IB : No device found` | A | E3：RCCL 文档 L216-222@`639370515b50` |
| B7 | **A 站未装 RCCL** ⇒ 三站不同构，当前只能 B↔C 两机 | A | E3：同上 L130-136@`639370515b50` |
| B8 | 内存带宽 ~256 GB/s LPDDR5X；同站叠并发被带宽顶起 ~2.8× | A | E3：`spec/d6-agent-standard/unsloth-a-station.md` L374@`e57db3e436c1` |
| B9 | Unsloth 官方口径：gpt-oss-120b **QLoRA ~65 GB VRAM**；MoE **不推荐 4-bit QLoRA**（BitsandBytes 不支持）→ 用 bf16 LoRA 或全量 | A | E3：同上 L118-130@`e57db3e436c1`（**转述 unsloth.ai，未回原文**，见 F3） |
| B10 | llama.cpp **不消费 RCCL**（自研 RPC + 层切分）；`-sm tensor` 在本链路 No-Go | A | E3：RCCL 文档 L52@`639370515b50` + `README.md` 一屏节 |
| B11 | 本仓明写「训练 / DDP / 微调 → **本仓无此负载**」 | A | E3：RCCL 文档 L71@`639370515b50` |

### 3.2 瓶颈量化（本批推算，非实测）

| # | 断言 | 级 | 依据 |
|---|---|---|---|
| C1 | 7B 全参 DDP（2 机，batch 4096 tokens）：单步计算 ≈ **7 s**，ring all-reduce 需搬 14 GB ≈ **13 s** ⇒ **通信 > 计算，加速比 < 1** | B | 推理链：① 梯度 = 7e9×2 B = 14 GB（依赖 B5 换算 1.1 GB/s）② 计算 = 6×N×tokens ÷ (峰值×MFU)，峰值取 60 TFLOPS bf16、MFU 取 20% ⇒ **峰值与 MFU 两个输入均无本集群实测**，标 E4 |
| C2 | LoRA（rank 16，可训 ~40 M）梯度 ≈ 80 MB ⇒ all-reduce **0.07 s**，可被计算完全掩盖 | B | 同链，仅梯度量变 ⇒ 结论对 MFU 不敏感（这是它比 C1 稳的原因） |
| C3 | 三站合计 384 GB UMA，但现役推理已占（gpt-oss-120b / DS V4-Flash 145G）⇒ 训练前须 `unload` | A | E1：`D:\RPC\ops\cluster.py` 命令面 + 本会话 ping 三站全不通（2026-11-11） |

⚠ **C1 的算力输入未经本地实测**：gfx1151 的 bf16 峰值与训练 MFU 在 `D:\RPC` 仓内**无读数**，60 TFLOPS / 20% 是外部估计。按框架纪律，这条属"推理链有 A 级证据但含未验证输入"⇒ **不得进设计结论，只进假设区**（§6.4）。

### 3.3 社区方案映射（★ 本批主产出）

| 瓶颈 | 社区方案 | 级 | 证据 | 对本集群判定 |
|---|---|---|---|---|
| 低带宽下梯度同步压垮计算 | **Deep Gradient Compression**：top-k 稀疏化 + 动量修正 + 掩码，压缩比 **270×~600×**，原文明写「enables large-scale distributed training on inexpensive commodity **1Gbps Ethernet**」 | A | arXiv **1712.01887v3**（Lin/Han/Mao/Wang/Dally，发布 2017-12-05，更新 2020-06-23） | ✅ **最对口**。14 GB → 23~52 MB，通信从 13 s 降到亚秒；本集群 1.1 GB/s 优于其 1 Gbps 前提 |
| 跨机同步本身可省 | **各站独立训 LoRA → 合并**：CAT（拼接式最优加权）优于既有 model-merging **43%**、优于 data-mixing **12%** | A | arXiv **2410.13025v2**（Prabhakar et al，2024-10-16 / upd 2024-12-02） | ✅ **最省事路径**，零新增通信依赖 |
| 同上，但有理论边界 | 加权平均的误差源于**梯度不匹配**，需 uncertainty-based 加权修正 | A | arXiv **2310.12808v2**（Daheim et al，2023-10-19 / upd 2024-08-23） | ⚠ 提示：三站数据分片若分布差异大，朴素平均会失效 |
| 跨机断点续训要传全部状态？ | **adapter-only handoff 足够**：41.9 M 参数的 LoRA 在两台 16 GB free-tier GPU 间续跑三 epoch QLoRA，**optimizer/scheduler 状态无需迁移** | A | arXiv **2504.15610v4**（Hosen，2025-04-22 / upd 2026-06-14） | ✅ 直接支撑"分站接力"形态，且用的就是 Unsloth |
| 单站容量装不下大模型 | **LoHan**：消费级单卡 + 有限主存微调 100B 级，首个在 RTX 4090 + 256 GB 内存上微调 175B | A | arXiv **2403.06504v2**（Liao et al，2024-03-11 / upd 2024-12-24） | ✅ 本集群 UMA 天然消除其主攻的 CPU↔GPU 搬运开销 |
| 选哪种并行方法 | **LLMem**：微调前预估显存，单卡误差 ≤1.6%、多卡 ≤3.0% | A | arXiv **2404.10933v1**（Kim et al，2024-04-16） | ✅ 可在 P-003 用作选型前置 |
| 反向传播内存/算力代价 | **ZO 优化**（MeZO 系）免 BP；块下降 + 梯度稀疏增强 | A | arXiv **2402.11592v3**（Zhang et al，2024-02-18 / upd 2024-05-28） | ⚠ 收敛慢，适合小数据 |
| 消费级卡训练效率未知 | RTX 4060 8 GB 实测：**PagedAdamW 提升吞吐至 +25%**（628 vs 500 tok/s）；**bf16 效率劣于 fp16** | A | arXiv **2509.12229v1**（Avinash，2025-09-07） | ⚠ **NVIDIA 数据，不可直迁**；但"bf16 可能劣于 fp16"对 RDNA3.5 是**值得优先验的假设** |
| 异构客户端 rank 不同 | **FSLoRA**（sketching 选子矩阵）/ **LoRA-FAIR**（服务端聚合偏差修正） | A | arXiv **2501.19389v4** / **2411.14961v3** | ◐ 三站同构，收益有限 |
| 无 RDMA 的通信栈本身 | RoCE 在超大规模的问题与替代 | A | arXiv **2302.03337v2**（Hoefler et al，2023-02-07 / upd 2023-04-15） | ◐ 背景参考，本集群连 RoCE 都没有 |

### 3.4 研究空白（含负面发现）

1. ★★★ **gfx1151 上的训练无任何第三方实测**。两个 StackExchange 站点各一次检索**零命中**（见 F3）；Unsloth 官方数据全在 A100/Colab/消费级 N 卡。⇒ 本集群若做训练，**第一个数字必须自己量**，无参照系。
2. **MoE 微调在 ROCm/RDNA 上的可行性未证**：B9 记 MoE 不宜 4-bit QLoRA，而本集群现役大模型（gpt-oss / Nemotron / DS V4）**全是 MoE** ⇒ 只能走 bf16 LoRA 或全参，而 bf16 在 RDNA3.5 的训练效率未知。
3. **DGC 未在 ROCm/RCCL 上验证过**：其实现基于 CUDA/PyTorch hook，移植到 gfx1151 无先例。
4. **三机 RCCL 从未测过**（A 站无 RCCL，B7）。
5. **跨机吞吐未测**：B3 只有 64 KiB 延迟读数，无大消息量吞吐。

## 4. 综合分析

### 4.1 关键发现总结

底座比一般"消费级集群"处境好——**跨机 collective 已实测通**（B3），缺的不是可行性证明而是**吞吐与算力读数**。而瓶颈的正确解法社区早已给出：**要么压缩梯度（DGC），要么根本不通信（独立训练 + CAT 合并）**。后者对本集群尤其合适，因为三站同构、UMA 容量充足。

### 4.2 技术 landscape（按"要不要跨机通信"分层）

| 层 | 形态 | 通信需求 | 本集群判定 |
|---|---|---|---|
| L0 | 各站独立训练 + 合并（CAT / 加权平均） | 仅首尾传文件 | ✅ **首选** |
| L1 | 分站接力（adapter-only handoff） | 仅传 adapter | ✅ 已有一手实证（2504.15610） |
| L2 | LoRA 跨机 DDP | 每步 ~80 MB | ✅ 可行（C2） |
| L3 | 全参 DDP + 梯度压缩 | 每步 23~52 MB（压缩后） | ⚠ 需移植 DGC |
| L4 | 全参 DDP 无压缩 | 每步 14 GB | ❌ 加速比 <1（C1，含未验证输入） |
| L5 | 张量并行 | 每层 all-reduce | ❌ 推理侧已判 No-Go（B10） |

### 4.3 研究空白

见 §3.4 五条。最关键的是第 1 条：**无参照系**，故 P-003 的实测优先级高于任何方案选型。

## 5. 幻觉抑制审查（Step 2 Review）

### 5.1 文献验证（F4 引用验证表）

验证方式 = **arXiv API 标识符检索命中**（机器可核，非 LLM 自任验证器）。读取日 **2026-11-12**。

| 引用 | ID | 验证方式 | 状态 |
|---|---|---|---|
| Deep Gradient Compression | arXiv 1712.01887v3 | API 检索命中 | 已验证（T1 命中） |
| LoHan | arXiv 2403.06504v2 | API 检索命中 | 已验证（T1 命中） |
| LLMem | arXiv 2404.10933v1 | API 检索命中 | 已验证（T1 命中） |
| 7B Advisor / adapter-handoff | arXiv 2504.15610v4 | API 检索命中 | 已验证（T1 命中） |
| LoRA/QLoRA on RTX 4060 | arXiv 2509.12229v1 | API 检索命中 | 已验证（T1 命中） |
| LoRA Soups (CAT) | arXiv 2410.13025v2 | API 检索命中 | 已验证（T1 命中） |
| Uncertainty-Based Gradient Matching | arXiv 2310.12808v2 | API 检索命中 | 已验证（T1 命中） |
| FSLoRA | arXiv 2501.19389v4 | API 检索命中 | 已验证（T1 命中） |
| LoRA-FAIR | arXiv 2411.14961v3 | API 检索命中 | 已验证（T1 命中） |
| ZO-LLM | arXiv 2402.11592v3 | API 检索命中 | 已验证（T1 命中） |
| Chameleon (SmartSwap) | arXiv 2509.11076v2 | API 检索命中 | 已验证（T1 命中） |
| Datacenter Ethernet and RDMA | arXiv 2302.03337v2 | API 检索命中 | 已验证（T1 命中） |
| PLoP | arXiv 2506.20629v1 | API 检索命中 | 已验证（T1 命中） |
| Multi LoRA Meets Vision | arXiv 2411.14064v1 | API 检索命中 | 已验证（T1 命中） |
| AMDKernelVault | arXiv 2609.12471v1 | API 检索命中 | 已验证（T1 命中，**CDNA 非 RDNA**，射程外备查） |
| SigmaTrace | arXiv 2610.24328v1 | API 检索命中 | 已验证（T1 命中） |
| NCCL EP | arXiv 2603.13606v3 | API 检索命中 | 已验证（T1 命中） |
| Byzantine-Resilient SGD + compression | arXiv 2005.07866v1 | API 检索命中 | 已验证（T1 命中） |
| Unsloth 官方加速数据 | — | 未回原文（WebFetch 被拦） | **未验证**（E3 转述，禁止作门禁判据） |
| gfx1151 训练社区实测 | — | 两站点检索 0 命中 | **未取证**（负面发现，非失败） |

**F4 表计数**：20 行 = 18 条 arXiv 已验证 + 2 条未验证/未取证（由本表逐行数得，非推算）。

### 5.2 技术声明验证

| 声明 | 方式 | 状态 |
|---|---|---|
| B1-B11 底座事实 | 读 `D:\RPC@3126626` 原文行号 | 已验证（E3 绑 hash） |
| DGC 压缩比与 1Gbps 结论 | arXiv abstract 原文 | 已验证（T1） |
| CAT 优于 merging 43% | arXiv abstract 原文 | 已验证（T1） |
| C1 加速比 <1 | 推算，含 2 个未实测输入 | **未验证**（入假设区） |
| bf16 在 RDNA3.5 效率 | 仅 N 卡旁证 | **未验证**（入假设区） |

### 5.3 待修正项

**自查（单视角）**（RULE-4）：本批检索、判读、撰写同为 Claude Opus 5，无对抗性。§3.2 的 C1 首版曾写成结论式表述，按"推理链含未验证输入即降级"改写为假设区条目。

**门禁状态**：Step 2 的 (a)-(d) 四项——(a) 无 FALSIFIED 断言；(b) 无 CONFLICT；(c) 阻断性断言 B1/B3/B5 均单源（`D:\RPC` 一处），**须标 `[单源-待二核]`** ⇒ 已在 §6.4 登记；(d) 假设区已转 C1/C2。

## 6. 对设计的输入

### 6.1 可用的技术方案

按 §4.2 的 L0→L5 分层。设计应**从 L0 起步**，L2 作为第二阶段，L3 需先验证 DGC 移植成本。

### 6.2 关键约束

- A 站无 RCCL ⇒ 任何跨机方案先要补装（B7）
- 三站离线 ⇒ 全部实测 blocked
- 现役模型全是 MoE ⇒ QLoRA 4-bit 路径基本不可用（B9）
- `NCCL_SOCKET_IFNAME` 必须显式设（B4），否则静默挂死

### 6.3 风险

| 风险 | 依据 | 缓解 |
|---|---|---|
| 训练与推理抢同一批机器 | C3 | 训练期显式 `unload`，走 `cluster.py` 唯一管理面 |
| 无参照系导致误判"我们太慢" | §3.4-1 | 先量自己的基线再谈优化 |
| 把 N 卡数据当本集群预期 | 2509.12229 等 | 所有外部数字标来源硬件，不进判据 |

### 6.4 未决项登记（四元块）

| 判据 | 触发条件 | 当前倾向 | 证据等级 |
|---|---|---|---|
| **B1/B3/B5 单源待二核**：全部来自 `D:\RPC` 一个仓 | 三站上线后复测 all_reduce | 二核 = 本仓自量，不引用第三方 | E3→E1 |
| gfx1151 bf16 训练峰值算力与 MFU | 首次训练实测 | 不预设，测完再定 C1 是否成立 | E4 |
| DGC 在 ROCm/RCCL 上的移植成本 | 决定做 L3 时 | 推迟——L0/L2 未做完不必碰 | E4 |
| 三站数据分片分布差异是否破坏朴素平均 | 做 L0 合并时 | 用 CAT 而非平均（2410.13025 支持） | E4 |
| Unsloth 官方数据回原文 | 网络通道恢复 | 必须回原文，否则 B9 不得进设计结论 | E3 |

## 7. 参考文献

**T1 一手（arXiv，读取日 2026-11-12，验证方式 = API 标识符检索）**

1. Lin, Han, Mao, Wang, Dally. *Deep Gradient Compression*. **arXiv:1712.01887v3**. 发布 2017-12-05 / 更新 2020-06-23.
2. Liao et al. *LoHan: Fine-Tune 100B on Consumer GPU*. **arXiv:2403.06504v2**. 2024-03-11 / 2024-12-24.
3. Kim et al. *LLMem: Estimating GPU Memory for Fine-Tuning*. **arXiv:2404.10933v1**. 2024-04-16.
4. Hosen. *Fine-Tuning a 7B Advisor on Free-Tier GPUs*. **arXiv:2504.15610v4**. 2025-04-22 / 2026-06-14.
5. Avinash. *Profiling LoRA/QLoRA on RTX 4060*. **arXiv:2509.12229v1**. 2025-09-07.
6. Prabhakar et al. *LoRA Soups: CAT*. **arXiv:2410.13025v2**. 2024-10-16 / 2024-12-02.
7. Daheim et al. *Model Merging by Uncertainty-Based Gradient Matching*. **arXiv:2310.12808v2**. 2023-10-19 / 2024-08-23.
8. Fang et al. *FSLoRA*. **arXiv:2501.19389v4**. 2025-01-31 / 2026-05-23.
9. Bian et al. *LoRA-FAIR*. **arXiv:2411.14961v3**. 2024-11-22 / 2025-10-12.
10. Zhang et al. *ZO-LLM*. **arXiv:2402.11592v3**. 2024-02-18 / 2024-05-28.
11. Wang et al. *Chameleon/SmartSwap*. **arXiv:2509.11076v2**. 2025-09-14 / 2026-07-15.
12. Hoefler et al. *Datacenter Ethernet and RDMA at Hyperscale*. **arXiv:2302.03337v2**. 2023-02-07 / 2023-04-15.
13. Hayou, Ghosh, Yu. *PLoP*. **arXiv:2506.20629v1**. 2025-06-25.
14. Kesim, Helli. *Multi LoRA Meets Vision*. **arXiv:2411.14064v1**. 2024-11-21.
15. Liu et al. *AMDKernelVault*（CDNA）. **arXiv:2609.12471v1**. 2026-09-11.
16. Baydamirli, Unat. *SigmaTrace*. **arXiv:2610.24328v1**. 2026-10-16.
17. Goldman et al. *NCCL EP*. **arXiv:2603.13606v3**. 2026-03-13 / 2026-04-02.
18. Data, Diggavi. *Byzantine-Resilient SGD*. **arXiv:2005.07866v1**. 2020-05-16.

**仓内取证（E3，绑 blob hash）**

- `D:\RPC@3126626`（2026-11-04）：`docs/research/2026-09-30_RCCL部署方案与集群必要性评估.md`@`639370515b50` · `spec/d6-agent-standard/unsloth-a-station.md`@`e57db3e436c1` · `docs/research/2026-09-16_分布式推理路线可行性调研_CIRU-Skulk-多机TP.md`@`36c754ac1203` · `spec/model-eval/FRAMEWORK-SURVEY-2026-09.md`@`913537d9c7ba`

**F5 先失败记录**：**N/A** —— 本批为纯文档（Step 1-2），无代码或 fixture 改动；F5 仅在 Step 9 触发。

## 修订历史

| 日期 | 版本 | 变更 |
|---|---|---|
| 2026-11-12 | v1.0 | 初版——P-001 上一轮口头分析正式化 + arXiv 18 源社区方案检索 + F1-F5 出具 |
| 2026-11-12 | v1.1 | Step 2 Review 就地补：B1/B3/B5 标 `[单源-待二核]`（双源规则）；C1 由结论降入假设区（推理链含未实测输入）；F4 表补 2 条未验证行的显式状态 |
