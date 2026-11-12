# 调研文档：a1-smoke-test（A-1 冒烟测试设计的前置取证）

---
id: a1-smoke-test-RESEARCH
type: design
version: 1.0
status: draft
date: 2026-11-12
depends: [distributed-sft-DESIGN]
upstream: null
---

> **批次**: P-008 · **档位**: T1（产出文档 + 后续动 `scripts/`）
> **本批定位**: A-1（Unsloth 能否在 gfx1151 训练）是 L0 的**单点否决闸**。本批不跑它，只把「怎么跑才算数」设计出来——因为否决闸若设计不当，会以假通过放行整条 L0。

## 1. 调研目标

为 A-1 冒烟测试取证两件事：① 社区/官方对 gfx1151 训练的**已声明事实**（决定测什么）；② `D:\RPC` 在本硬件上踩过的坑（决定**假绿会藏在哪**）。

## 2. 调研方法

### 2.1 使用的工具与降级链（F3）

| 目标通道 | 状态 | 实际通道 | 读到的事实 |
|---|---|---|---|
| `mcp_english-search.search_web` | ❌ 522（本批 1 次） | `WebFetch` 直取官方文档 | 见 §3.1 |
| `WebFetch` → `docs.unsloth.ai/getting-started/installation` | ◐ 301 重定向未自动跟 | 跟重定向 `unsloth.ai/docs/...` | 页面 404，但返回体给出 `?ask=` 查询模式 |
| `WebFetch` → `unsloth.ai/docs/get-started/install.md?ask=…` | ✅ **可用** | 同 | ★ 本批全部 T1 证据来源（官方文档直接问答，返回逐字引文） |
| `mcp_stackexchange` | ✅ 可用但零命中 | — | `PyTorch ROCm silently falls back to CPU training` = **0 命中** ⇒ CPU fallback 问题在 SO 无现成答案，须自设断言 |
| `Bash`/`grep` 读 `D:\RPC@3126626` | ✅ | 同 | §3.2 全部 |

### 2.2 调研范围

Unsloth 官方 AMD 安装与训练文档（T1）· `D:\RPC` 的 unsloth/ROCm 踩坑实录（E3 绑 hash）· 本仓 P-005/P-006 已确立的取证纪律。

## 3. 调研发现

### 3.1 官方声明（T1，逐字引文，读取日 2026-11-12）

| # | 断言 | 级 | 引文（官方 `?ask=` 返回） |
|---|---|---|---|
| U1 | **Unsloth 官方支持 gfx1151 做 LoRA 训练** | A | "Yes. Unsloth supports LoRA fine-tuning on AMD GPUs, including `gfx1151`" |
| U2 | 支持架构面覆盖 RDNA 1–4 与 CDNA 1–4，Strix Halo 三型全列 | A | "RDNA 1–4: … Strix Halo/Ryzen AI MAX (`gfx1150`, `gfx1151`, `gfx1152`)"；"CDNA 1–4 … listed as Linux-only" |
| U3 | ROCm 版本门槛与 wheel tag 映射规则 | A | "requires **ROCm 6.0 or newer**"；"ROCm 6.5–6.9 uses `rocm6.4`"；"ROCm 7.3+ uses `rocm7.2`" |
| U4 | 官方安装序列（含两个关键 pin） | A | `uv pip install "torch<2.15" … --index-url …/whl/rocm7.2`；`echo "triton ; sys_platform == 'never'"`；`echo "xformers ; sys_platform == 'never'"`；`uv pip install "unsloth[amd]" --overrides torch-pins.txt` |
| U5 | 必设 env | A | `export HF_HUB_DISABLE_XET=1` |
| U6 | FA2 默认不装，走 SDPA | A | "Flash Attention 2 is not installed by default; PyTorch SDPA is used" |
| U7 | ★ **不带 pins 升级会把 ROCm torch 换成 CUDA wheel** | A | "Avoid upgrading Unsloth without the saved pins, which can replace ROCm PyTorch with a CUDA wheel" |
| U8 | **分布式训练仅 Linux** | A | "Distributed training is Linux-only" |
| U9 | ★ **官方自带 smoke test 参数** | A | "4-bit loading, LoRA rank and alpha `16`, batch size `1`, gradient accumulation `4`, and `max_steps=60`" |
| U10 | QLoRA 4-bit 在 gfx1151 支持 | A | "Unsloth documents bitsandbytes-based 4-bit QLoRA on AMD GPUs" |
| U11 | MoE 需 expert→linear 转换才能量化 | A | "converts the MoE expert weights into linear layers so bitsandbytes can quantize them"，但 "This is not confirmation that an unmodified bitsandbytes setup supports the model" |
| U12 | ★★ **「AMD 4-bit」与「gpt-oss QLoRA」两条各自覆盖，组合未确认** | A | "the docs cover AMD 4-bit QLoRA and gpt-oss QLoRA separately, but don't explicitly confirm that exact combination" |
| U13 | ★★★ **4-bit 冒烟通过不验证 bf16 路径** | A | "A passing 4-bit smoke test also won't validate the BF16 path" |

### 3.2 `D:\RPC` 本集群实际经验（E3，绑 blob hash）

| # | 教训 | 对冒烟测试的含义 | 证据 |
|---|---|---|---|
| R1 | **unsloth bundled ROCm lib 与系统 ROCm symbol 不匹配**（`hsa_amd_queue_create`） | 环境断言必须查**实际加载的 lib 路径**，不能只查装了哪个包 | E3：`spec/d6-agent-standard/unsloth-a-station.md` L346@`e57db3e436c1` |
| R2 | 「运行期实际加载的那一份 ★ 容易看错」——RCCL 测的是 venv 那份而非系统包 | 同上：`ldd`/`/proc/<pid>/maps` 级取证，不接受包管理声明 | E3：`docs/research/2026-09-30_RCCL…md` §2.2@`639370515b50` |
| R3 | **三站 ROCm 版本不同构**：A 站 HIP 7.13（7.x 线），B/C 装 ROCm 10.0 | 冒烟必须**逐站**跑，一站通过不代表他站；且 wheel tag 映射（U3）各站不同 | E3：unsloth-a-station L346 + RCCL 文档 §4.1@`639370515b50` |
| R4 | **设不存在的环境变量不报错，只静默失效**（`RCCL_SOCKET_IFNAME` 教训） | 所有 env 前置（U5 等）须**读回验证**，不能设了就算 | E3：RCCL 文档 §4.4@`639370515b50` |
| R5 | gfx1151 上 llama.cpp **HIP 后端有 dense 模型输出损坏**（#27579）、**decode 随 context 悬崖**（#27856），ROCm 10 仍未关闭 | 本集群在 gfx1151 上**已有"计算结果错但不报错"的先例** ⇒ 冒烟必须验数值正确性，不能只看没崩 | E3：unsloth-a-station §9.4@`e57db3e436c1` |
| R6 | A 站 unsloth studio / LM Studio 进程**不响应 `/health`**（404） | 存活探针不能用 /health，须换判据 | E3：`ops/cluster_ssh.py` L141 注释 |
| R7 | B 站缺 `iommu=pt`，C 站 `amd_iommu=off` ⇒ **不是单变量环境** | 跨站对比时站点差异是混杂变量，须记录内核参数 | E3：RCCL 文档 §7-6@`639370515b50` |
| R8 | B 站现有 venv 实测 `torch 2.12.0+rocm7.15.0a` / **Python 3.14** | 满足 U3 的 `rocm7.2` tag 与 `torch<2.15`；但官方示例用 3.13 ⇒ **Python 版本差异需测** | E3：RCCL 文档 §4.3@`639370515b50` |

### 3.3 ★ 本批推翻的既有认知（三条）

| 原说法 | 出处 | 推翻依据 |
|---|---|---|
| 「Unsloth 官方加速数据多在 colab/A100/消费级测得，**A 站具体显卡需自跑 benchmark**」 | `D:\RPC` unsloth-a-station §5.2 | U1 官方**明列 gfx1151 支持** ⇒ 不是"没数据"，是"本集群未自证"。A-1 由 E5 纯推测升为「有 T1 声明、待本地复现」 |
| 「**MoE 不推荐 4-bit QLoRA**：BitsandBytes 不支持 MoE 4bit」 | 同上 §5.2 | U10/U11：Unsloth 走 **expert→linear 转换**绕开该限制 ⇒ 原说法只对 unmodified bnb 成立，对 Unsloth 路径不成立（但组合未确认，见 U12） |
| 本仓 P-002 记「Unsloth 官方数据全在 A100/Colab/N 卡」 | `distributed-sft/RESEARCH.md` §3.4-1 | U1-U13 直接反证 ⇒ **该条已回写更正** |

⚠ 第三条是**本仓自己的错误**：P-002 当时只读了 `D:\RPC` 的二手记录就写「官方无 AMD 数据」，未回原文。已入 M7 样本 6。

## 4. 综合分析

### 4.1 关键发现总结

A-1 的**答案大概率是"能"**（U1 官方明列），但真正的问题不是能不能，而是**冒烟怎么设计才不会假绿**。三条最危险：U7（升级悄悄换回 CUDA wheel）、U13（4-bit 通过不代表 bf16 通过）、R5（本硬件已有"算错不报错"先例）。

### 4.2 landscape：假绿的四个藏身处

| 藏身处 | 为什么会假绿 | 反制 |
|---|---|---|
| **CPU fallback** | 训练"跑完"但全程在 CPU，慢得像 GPU 故障反而被当成正常 | 断言 device + 训练前后 GPU 侧计数变化 |
| **CUDA wheel 冒充** | `torch.version.hip` 为 None 时训练仍可"成功"（在 CPU 上） | 断言 hip 非 None + 实际加载 lib 路径 |
| **只 forward 没 backward** | 加载模型 + 前向不报错，被记成"训练通了" | 断言梯度非 None + **参数真的变了** |
| **数值错但不崩** | R5 先例：HIP 在 gfx1151 上产出损坏输出而退出码 0 | 与 CPU 参考实现做**数值对照**，不只看没崩 |

### 4.3 研究空白

官方 `?ask=` 返回的是文档综合答案，**非单一页面逐字** ⇒ U1-U13 的引文可复核但页面定位需再核（已标 F1 读取日）。

## 5. 幻觉抑制审查（Step 2 Review）

### 5.1 文献验证（F4）

| 引用 | ID/定位 | 验证方式 | 状态 |
|---|---|---|---|
| Unsloth AMD 支持声明 | `unsloth.ai/docs/get-started/install.md?ask=…` | WebFetch 实取，返回逐字引文 | 已验证（T1 命中） |
| Unsloth 安装 pin 序列 | 同上 | 同上 | 已验证（T1 命中） |
| 「Distributed training is Linux-only」 | 同上 | 同上 | 已验证（T1 命中） |
| U12/U13 两条缺口 | 同上 | 同上 | 已验证（T1 命中，**官方自陈未确认**） |
| R1-R8 | `D:\RPC@3126626` 行号 | 读原文 | 已验证（E3 绑 hash） |
| CPU fallback 社区案例 | stackexchange | 检索 0 命中 | **未取证**（故须自设断言，不能引现成结论） |

### 5.2 技术声明验证

见 §3.1/§3.2 逐条。⚠ U1-U13 的引文来自文档问答接口，**建议 Step 5 前用页面直取复核一次**（登记 §6.4）。

### 5.3 待修正项

**自查（单视角）**（RULE-4）：本批取证与撰写同基座。已知的自我纠正在 §3.3——三条推翻性发现里，**两条推翻的是 `D:\RPC` 的二手记录，一条推翻的是本仓 P-002 自己的结论**，后者已入 M7。

## 6. 对设计的输入

### 6.1 可用的技术方案

冒烟测试应**照官方 smoke test 参数起步**（U9），不自己发明基线；双臂（4-bit + bf16）由 U13 强制；环境断言层（G0）由 U7/R1/R2/R4 决定其必要性。

### 6.2 关键约束

- 三站不同构（R3）⇒ 逐站跑，且 wheel tag 按各站 ROCm 版本映射（U3）
- 无 `iommu=pt`（R7）⇒ 内核参数须入证据包
- 本批不实跑（A-9 已裁）⇒ 只出设计与脚本，跑待硬件

### 6.3 风险

| 风险 | 依据 | 缓解 |
|---|---|---|
| 冒烟假通过放行 L0 | §4.2 四藏身处 | 六闸门串行，前一不过不开后一 |
| 冒烟本身跑不起来（环境装不上） | U4 序列复杂、pin 易错 | G0 单独成闸，装不上就报"环境未就绪"而非"A-1 失败" |
| 把"官方支持"当"本集群支持" | U1 vs R3 | 判据只认本集群读数 |

### 6.4 未决项登记（四元块）

| 判据 | 触发条件 | 当前倾向 | 证据等级 |
|---|---|---|---|
| U1-U13 用页面直取复核（现为 `?ask=` 综合答案） | Step 5 落脚本前 | 必复核——引文可核但页面定位未定 | E3 |
| Python 3.14（B 站现状）vs 官方 3.13 是否影响 | G0 实跑时 | 倾向按官方 3.13 建独立 venv，不动现有 vllm-rocm | E4 |
| 数值对照的参考实现选什么（CPU bf16 精度差多少算异常） | G3 前 | 未定 | E4 |

## 7. 参考文献

**T1 一手**：Unsloth 官方文档 `https://unsloth.ai/docs/get-started/install.md`（经 `?ask=` 问答接口，读取日 2026-11-12）——U1-U13 全部出处。

**仓内取证（E3 绑 hash）**：`D:\RPC@3126626`：`spec/d6-agent-standard/unsloth-a-station.md`@`e57db3e436c1` · `docs/research/2026-09-30_RCCL部署方案与集群必要性评估.md`@`639370515b50` · `ops/cluster_ssh.py` L141。

**F5 先失败记录**：**N/A** —— 本批为纯文档（Step 1-2），无代码改动；F5 在 Step 9 触发。

## 修订历史

| 日期 | 版本 | 变更 |
|---|---|---|
| 2026-11-12 | v1.0 | 初版——Unsloth 官方 13 条 T1 声明 + `D:\RPC` 8 条本集群经验 + 三条推翻性发现 + 假绿四藏身处 |
