# Spec_Runner

薄壳 spec 工作流 runner——Spec_Workflow P-009 方案 B 的执行器（stdlib only，零框架依赖，Python ≥3.8）。

> **P-019 归巢注（2026-09-08）**: 本 runner 原为独立仓库 `F:\Spec_Runner`（commit 4ea703d→71c7ae6 共 5 个），
> 经 P-019 调研（RESEARCH v1.1 A6 实证：外仓无 remote/全 commit 服务本仓，D1「独立生命周期」论据弱化）
> 用户裁决并入本仓 `tools/spec_runner/`——单仓管理便利 + 事件流证据（E1）与 M7 账本同仓可读。
> 外仓 `F:\Spec_Runner` 冻结为历史存档。设计规格：
> `spec/spec-runner/SPEC_RUNNER_DESIGN.md`（D1-D7）；归巢设计：`spec/spec-runner-homing/SPEC_RUNNER_HOMING_DESIGN.md`（D1-D4）。

## 定位

把 spec 工作流的三个已实证痛点物理化：

1. **门禁物理化**——`gate` 命令 + `--require-gate` 前置检查（审查 gate 未过，实施不可启动）
2. **跨会话状态持久化**——append-only JSONL 事件流（state = 事件流的派生视图）
3. **取证副产物化**——事件流即 E1 级证据，`replay` 即复现

sessions 默认落 `tools/spec_runner/sessions/`（由 `__file__` 派生；`SR_SESSIONS_DIR` env 可注入）。

## 命令面

```bash
# 流程门禁：执行命令 + exit 透传 + 事件入流（verdict = exit code 机械映射）
python spec_runner.py gate --name dc-validator \
    --cmd "python scripts/dc_validator.py --check-all" \
    --session p016-review-001 --cwd <workdir>

# LLM 运行：装配 prompt → 端点预检（不可达即 exit 1）→ 请求/响应入流
python spec_runner.py run --task review --session p016-review-001 --resume \
    --require-gate dc-validator \
    --prompt-file task.md \
    --endpoint http://192.168.1.11:1234 --model <m> --provider lm-studio-a

# 派生视图（状态 = 重放事件流）
python spec_runner.py status [--session <sid>]

# 重放校验：seq 单调 + 每行可解析 + llm_request 装配载荷完整
python spec_runner.py replay --session <sid>

# fork：复制前 N seq 行至新流
python spec_runner.py fork --session <sid> --seq 42 --new <sid2>

# fork + 返工图登记（P-089 可选三件，all-or-none；成功后追加一条边至 docs/rework-graph.json）
python spec_runner.py fork --session <sid> --seq 42 --new <sid2> \
    --reason "<一句返工原因，非空>" --trigger-kind upstream-overturned \
    --provenance manual:<载荷>
#   值域读真值源（trigger_kinds / provenance_prefixes）；校验先于 fork、失败即 exit 2 零写入；
#   完整判定单点在对账器 scripts/rework_graph_check.py（薄壳只做写入端 fail-fast 子集）

# 决策产物管线校验（P-020）：decision 事件链 schema/evidence/step 序（只读）
#   必须显式声明二选一（P-132）：--expect 期望完整链 / --legacy 仅校验已登记链内部一致性
python spec_runner.py step-gate --session <sid> --expect research design implement verify finalize
python spec_runner.py step-gate --session <sid> --legacy

# 检索 = grep（零代码）：
#   grep '"source": "gate"' sessions/<sid>.jsonl   # 门禁轨迹
#   grep '"event": "decision"' sessions/<sid>.jsonl # 决策记录轨迹
python spec_runner.py selftest   # 83 项内置自测（stdlib mock server）
```

端点/模型/提供商运行时注入：`--endpoint/--model/--provider` 或 `SR_ENDPOINT/SR_MODEL/SR_PROVIDER` 环境变量——不硬编码。

## 事件流

`sessions/<session_id>.jsonl`，每行一个事件（十字段 schema）：

```json
{"ts": "...", "seq": 42, "session": "p016-review-001", "source": "gate",
 "model": null, "provider": null, "event": "gate",
 "input": {"cmd": "...", "cwd": null},
 "output": {"stdout_tail": "...", "exit": 0},
 "gate": {"name": "dc-validator", "cmd": "...", "exit": 0, "verdict": "pass",
          "stdout_tail": "..."}}
```

- `seq` 流内单调递增（append-only 的机械保证，`replay` 校验）
- `source` 五档：system / user / assistant / tool / gate（按来源过滤 = 文本版 Trajectory）
- `model`/`provider`：LLM 事件（llm_request/llm_response）必填——RULE-5 异质性追溯锚
- `event: "decision"`：决策产物管线事件（P-020）——`input` = FWK-DECISION-RECORD 八字段
  dict（`metadata.step_id/step_seq` 标识流程步骤、`metadata.evidence` 数组 = 决策证据锚点
  E1-E4）；由 `step-gate` 命令只读校验（schema 完整 / evidence 非空 / step 序单调恰一条）
- 写入端单点把守：schema 违规 / seq 非递增在写入器抛错拒绝落盘
- 同 session 复用必须显式 `--resume`（RULE-1 时序独立物理化）

## 约束

- Python ≥3.8，stdlib only（无第三方依赖，无供应链面）
- adapter 开放结构：`NativeHTTPAdapter`（默认，OpenAI 兼容 API 裸调）；
  dsh SDK 为实测后升级候选（换 adapter 不动核心）
- 与 Spec_Workflow 双向零依赖：本 runner 不内置其路径；其校验器不调用本 runner
- **git 快照 = opt-in（P-022 懒加载，默认关）**：`gate`/`run` 后的事件流持久化
  提交需显式设 `SR_GIT_AUTOCOMMIT=1` 才激活；激活后**只提交本次实际写入的
  `<sid>.jsonl` 单文件**（不再整目录清扫），提交带 `--no-verify`（透明快照不被
  仓级 pre-commit 中间态打断）。会话目录不在 git 仓内 → 静默跳过。未激活时
  持久化由仓库既有 pre-commit + 人工 commit 承担（事件流文件本身已落盘）

## 其他项目接入（模板）

`templates/spec_runner_adapter.py` 是通用接入样板——复制到目标项目、只改顶部配置区
（`RUNNER` 绝对路径 / `PREFIX` 项目标识 / `CWD` 工作目录 / `GATES` 门禁表）即可：

```bash
cp templates/spec_runner_adapter.py <你的项目>/scripts/
# 改配置区后……
python scripts/spec_runner_adapter.py gates        # 列出可用门禁
python scripts/spec_runner_adapter.py gate unit-tests   # 跑门禁（exit 透传）
python scripts/spec_runner_adapter.py probe        # 接入自检（一个 echo 探针 gate）
python scripts/spec_runner_adapter.py dry-run gate unit-tests  # 预览命令不执行
```

要点：模板是编排壳（不复制 runner 逻辑、不改 gate 语义、不引入依赖）；session 自动
按 `{PREFIX}-{name}-{yyyymmdd}` 命名；`gate` 可嵌套进项目自己的 pre-commit/CI
（exit 透传）。CWD 默认 = 模板所在目录的父目录（常见 `scripts/` 布局）。

### 具体接入示例

`templates/examples/spec_workflow_adapter.py` 是**已配置成品**（Spec_Workflow 自举：
`PREFIX=specwf` / `CWD=F:\Spec_Workflow` / `RUNNER` 指向本目录 `spec_runner.py` /
`GATES` = dc-validator + m7-stats + repo-stats + pre-commit 四门禁）——新项目照它改
`RUNNER / PREFIX / CWD / GATES` 四处即可，避免从空白样板摸索门禁表写法：

```bash
# 预览（不执行）——观察命令装配是否如预期
python tools/spec_runner/templates/examples/spec_workflow_adapter.py dry-run gate dc-validator
# 接入自检——一个 echo 探针 gate 真实入流（验证 = 事件流落在 sessions/specwf-probe-*）
python tools/spec_runner/templates/examples/spec_workflow_adapter.py probe
python tools/spec_runner/spec_runner.py replay --session specwf-probe-YYYYMMDD  # 重放校验
```

### 调研步接入候选（gpt-researcher，官方文档确认 2026-09-08）

研调步（Spec 工作流 Step 1）弹药层可选接 **gpt-researcher**——官方文档确认支持
自定义 OpenAI 兼容端点：`OPENAI_BASE_URL` 指向本地 OpenAI 兼容服务 + `FAST_LLM`/
`SMART_LLM=openai:<端点内模型名>`；三机 LM Studio（OpenAI 兼容，P-009/P-010 已
实测）可直接接入，无需云端 key。搜索轴 `TAVILY_API_KEY` 可替换为 `duckduckgo`/
`searx` 等（免商业 key）。提供 MCP 形态（规划者-执行者 + 引用报告；多代理流水线
含 Reviewer「研究-审核-修正」循环）。接入形态 = MCP/HTTP 独立服务调用——不经
runner 的 gate（gate 的 verdict 仍是验证命令 exit code 机械映射）。官方文档：
https://docs.gptr.dev/docs/gpt-researcher/llms