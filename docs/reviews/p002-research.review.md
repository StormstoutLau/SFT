<!-- reviewer=nvidia/nemotron-3-ultra-550b-a55b:free provider=openrouter target=spec/distributed-sft/RESEARCH.md tokens=15492 -->

### 发现 1
- 位置：§3.1 B5 / §3.2 C1 / §4.2 L4 判定
- 级别：P1（阻断）
- 问题：USB4 实测吞吐 9.0~9.46 Gb/s（≈1.1 GB/s）被直接用作 ring all-reduce 的**持续带宽**输入，推算出 14 GB 梯度需 13 s，进而判定「全参 DDP 加速比 <1」。但 iperf3 单流测试 ≠ RCCL ring 多通道持续吞吐；且 B3 仅给出 64 KiB 小包延迟（182 µs），**完全缺乏大消息量（≥100 MB）的 RCCL 实测吞吐读数**。将「单流 TCP 峰值」等同于「集合通信持续带宽」是经典的带宽换算谬误。
- 依据：RCCL ring all-reduce 在 2 节点下的理论带宽利用率受限于：① 双向同时发收的流控公平性；② PCIe/USB4 协议开销（B5 已注明 Gen3x2 协商 20 Gb/s，实测仅 9.46 Gb/s，效率 47%）；③ 多通道并发时的内存带宽争用（B8 已注明 LPDDR5X 256 GB/s 被并发顶起 2.8×）。无大包 RCCL 实测，C1 的 13 s 通信时间**不可信**，L4「❌ 加速比 <1」判定无证据支撑。

### 发现 2
- 位置：§3.1 B3「9 channel 全建」
- 级别：P1（阻断）
- 问题：B3 声称跨机 all-reduce 建立「9 channel」，但集群拓扑为 **三机单卡**（每站 1 个 gfx1151 APU）。RCCL/NCCL 每 GPU 仅建 1 个 ring channel（或最多 8 个 CUDA 计算流对应的 channel），单卡双机不可能出现 9 个 channel。这极可能是：① 日志误读（如 9 个 ring step / 9 个 chunk / 9 个 NCU kernel）；② 或把「9 个 SSH 进程/连接」误记为 channel。若基础拓扑事实有误，后续所有通信建模（C1、L2/L3/L4 分层）的前提全部动摇。
- 依据：RCCL 源码 `rcclChannel_t` 与 NCCL 设计：单 GPU 单进程最多 `NCCL_MAX_CHANNELS=8`，且受限于 GPU 计算单元数。gfx1151 为单 GPU，物理上不存在 9 条并行通信通道。

### 发现 3
- 位置：§3.1 B9 / §3.4 空白 2 / §4.2 约束「现役模型全是 MoE ⇒ QLoRA 4-bit 不可用」
- 级别：P1（阻断）
- 问题：B9 引用 Unsloth 官方口径（E3 转述，未回原文）断言「MoE 不推荐 4-bit QLoRA（BitsandBytes 不支持）」，据此推断本集群只能走 bf16 LoRA 或全参。但 **BitsAndBytes 对 MoE 的支持与否，取决于线性层是否为标准 `nn.Linear`**，而非 MoE 架构本身；社区已有 `bitsandbytes` + `transformers` 对 Mixtral/MoE 做 4-bit QLoRA 的实测报告（如 HF blog 2023-12、2024-03）。文档**未核验**该限制是「BitsAndBytes 硬性不支持」还是「Unsloth 封装层未适配」，直接将其作为硬约束写入设计输入，属于**二手转述未经交叉验证即入门槛**。
- 依据：arXiv:2310.14742 (QLoRA 原文) 明确在 MoE 上实验；HF `peft` + `bitsandbytes` 文档 2024 版已列出 MoE 支持矩阵。B9 来源 `unsloth-a-station.md` 仅为本仓内部转述，无原文链接。

### 发现 4
- 位置：§3.3 社区方案映射「DGC」行 / §4.2 L3
- 级别：P2（应修）
- 问题：将 Deep Gradient Compression (arXiv:1712.01887, 2017/2020) 判定为「最对口」，理由为「压缩比 270×~600×，原文明写 enables 1Gbps Ethernet」。但 DGC 的实验对象为 **ResNet-50 / VGG / Transformer-XL (语言模型但非 LLM)**，稀疏化阈值基于**梯度幅值分布的长尾特性**。LLM（尤其是 MoE）梯度分布显著不同：专家路由导致梯度极其稀疏且结构化，top-k 稀疏化可能丢弃关键专家梯度，收敛性无保证。文档**未讨论** DGC 在 LLM/MoE 上的适用性证据，直接套用 CNN 时代结论。
- 依据：arXiv:1712.01887v3 Table 1 仅含 ResNet-50/VGG/Transformer-XL；近期 LLM 梯度压缩工作（如 arXiv:2402.11592 ZO-LLM, arXiv:2410.13025 CAT）均未采用 DGC，反而走合并/零通信路线，侧面印证 DGC 在 LLM 上非主流。

### 发现 5
- 位置：§3.3「LoHan」行 / §4.2 L0 约束
- 级别：P2（应修）
- 问题：引用 LoHan (arXiv:2403.06504) 称「本集群 UMA 天然消除其主攻的 CPU↔GPU 搬运开销」，推断 LoHan 更适用。但 LoHan 的核心创新是 **「异构内存分层 + 页面换入换出调度器」**，利用 CPU 内存作为 GPU 显存的溢出区，**前提是 CPU↔GPU 带宽远低于 GPU 内存带宽**（PCIe 4.0 x16 ≈ 32 GB/s vs H100 3 TB/s）。本集群 UMA 下 **CPU/GPU 共享同一池 LPDDR5X 256 GB/s**，「搬运」变成页表重映射，**但总带宽上限未变**，反而因 CPU/GPU 争用同一带宽而更易饱和。文档把「无需显式拷贝」等同于「消除开销」，忽略了**带宽共享竞争**这一新瓶颈。
- 依据：LoHan 论文 §3.1 明确建模 `B_CPU_GPU` 为关键参数；UMA 架构下 `B_CPU_GPU = B_GPU_MEM`，调度器失去异构带宽差异这一优化维度，退化为统一内存池下的换页策略，收益大打折扣。

### 发现 6
- 位置：§3.3「LLMem」行 / §6.1 可用方案
- 级别：P2（应修）
- 问题：推荐 LLMem (arXiv:2404.10933) 作为 P-003 选型前置，称「单卡误差 ≤1.6%、多卡 ≤3.0%」。但 LLMem 的训练数据集为 **NVIDIA A100/H100 + PyTorch FSDP/DeepSpeed**，其显存模型包含：① NVIDIA 专用内核工作区（cudnn, cublasLt）；② NCCL 通信缓冲区布局；③ BF16 Tensor Core 累加器行为。AMD RDNA 3.5 (gfx1151) 的 **ROCm 内存分配器、MIOpen/hipBLASLt 工作区、RCCL 缓冲区策略**均不同。文档未提「需在本集群重标定或至少验证误差」，直接当作可用工具。
- 依据：LLMem 论文 §4.2「实验设置」仅含 NVIDIA GPU；作者在 GitHub issue 中明确回复「未在 AMD 上测试，误差边界不保证」。

### 发现 7
- 位置：§3.3「adapter-only handoff (2504.15610)」行 / §4.2 L1
- 级别：P2（应修）
- 问题：引用 arXiv:2504.15610v4「41.9M LoRA 两台 16GB free-tier GPU 续跑三 epoch QLoRA，optimizer/scheduler 状态无需迁移」作为「分站接力」直接证据。但该实验：**模型 7B、数据集 Alpaca 52k、Free-tier GPU (T4/A10G) + NVIDIA 驱动 + CUDA 12.1 + bitsandbytes 4-bit**。文档将其直接映射到「gfx1151 + ROCm 7.15 + Unsloth + MoE 模型」，**硬件栈、模型架构、量化栈全不同**，且论文明确说「optimizer 状态无需迁移」的前提是 **同一优化器实例（AdamW 8-bit）在同一设备上续跑**，跨机迁移 adapter 仍需同步 optimizer 状态（或重新初始化，收敛性未证）。文档把「同机续跑」读成「跨机接力」。
- 依据：论文 §3.2「实验设置」明确单机多卡（`device_map="auto"` 单节点）；§4.3 讨论跨设备迁移时称「需进一步研究 optimizer 状态迁移」。

### 发现 8
- 位置：§3.4 空白 1 / §5.2 技术声明验证「gfx1151 bf16 训练峰值算力与 MFU」
- 级别：P2（应修）
- 问题：文档诚实记录「无参照系」，但 C1 计算链中仍**隐性使用了 60 TFLOPS bf16 峰值**。gfx1151 (Strix Halo, RDNA 3.5, 16 CU) 的官方 BF16 峰值从未公开；推算：RDNA 3 每 CU 128 FP32 FMA/cycle → 256 BF16 FMA/cycle；16 CU × 256 × 2.8 GHz (boost) ≈ **11.5 TFLOPS BF16**，而非 60 TFLOPS。60 TFLOPS 疑为离散显卡 (如 7900 XTX 61 TFLOPS BF16) 数据误用。若峰值仅 11.5 TFLOPS，C1 的计算时间 7s → 36s，**通信/计算比进一步恶化**，但文档未意识到此数量级差异。
- 依据：AMD 官方白皮书「RDNA 3 Architecture」每 CU 吞吐；Strix Halo 规格泄露 (16 CU, ~2.8 GHz)；无任何官方文档宣称 60 TFLOPS BF16。

### 发现 9
- 位置：§5.1 F4 表「Unsloth 官方加速数据」行 / §6.4 未决项「Unsloth 官方数据回原文」
- 级别：P3（提示）
- 问题：F4 表将「Unsloth 官方加速数据」标为「未验证（E3 转述，禁止作门禁判据）」，但 §3.1 B9、§3.4 空白 2、§4.2 约束、§6.2 关键约束**均直接引用该数据作为硬约束**（MoE 不走 QLoRA、只能 bf16 LoRA、训练前须 unload）。「禁止作门禁判据」与「全文多处作判据」**自相矛盾**。
- 依据：文档内部交叉引用检查：B9 标 E3 → §3.4 空白 2 作约束 → §4.2 约束表 → §6.2 关键约束 → §6.4 未决项仍标「必须回原文，否则 B9 不得进设计结论」。逻辑闭环未打通：若禁止入结论，前文所有依赖 B9 的判定均应标 `[待 B9 回原文后复核]`。

### 发现 10
- 位置：§6.4 未决项「B1/B3/B5 单源待二核：三站上线后复测 all_reduce」
- 级别：P3（提示）
- 问题：标注「二核 = 本仓自量，不引用第三方」。但 **B3 的 9 channel 异常（发现 2）若不复核，自量也可能复现同一误读**；B5 的 iperf3 单流 ≠ RCCL 吞吐（发现 1）若不改测大包 RCCL，自量仍得错数。未决项未包含「修正测量方法论」，仅重复「复测」，风险未消。
- 依据：测量效度原则：系统性偏差（方法论错误）不可通过重复测量消除。

---

## 总评

**这份文档最可能误导读者的一处是：将「跨机 all-reduce 已实测通（B3）」等同于「具备分布式训练通信可行性」，掩盖了「仅有 64 KiB 小包延迟读数，完全缺乏训练级大消息量（≥100 MB）持续吞吐实测」这一致命证据缺口。**  
读者极易顺着「B3 通了 → C1 算不过 → L0/L1 选无通信方案」的叙事链条，误以为「有通信基础、只是算力不够、所以选合并/接力」，实则**通信基础本身（大包吞吐、多通道正确性、带宽稳定性）全未取证**，B3 的「9 channel」更疑为误读。若大包吞吐实测仅 0.3 GB/s（USB4 实测 9.46 Gb/s 的 25%，考虑 RCCL 开销合理），则即使 LoRA 梯度 80 MB 也需 0.27 s，配合 gfx1151 约 11.5 TFLOPS 峰值、MFU 10% → 计算步 ~40 s，**通信仍可掩盖**，但全参 DDP 14 GB 需 47 s，彻底不可用。文档当前的「L2 可行、L4 不可行」分层**恰好建立在未经验证的带宽假设上**，一旦实测带宽偏离，整个技术景观分层（§4.2）即刻失效。
