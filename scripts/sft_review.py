#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""RULE-5 异构审查器 —— 用非本地基座对本文档做对抗性审查

为什么需要：本仓此前所有 Review 轮都是**同一基座既写又审**（RULE-4 只能标「自查（单视角）」）。
RULE-5 要求 reviewer 与 implementer 用**异构基座**——同基座新会话只消除记忆污染，
不消除同分布盲区。

端点与密钥来源：`D:\RPC\secrets\`（ADR-0003 铁律：key 只存 secrets/，禁止复制进脚本/文档）。
本脚本运行时读取，绝不写盘。可用 env `OR_KEY_FILE` / `OR_BASE` / `OR_MODEL` 覆盖。

★ 为什么不用 spec_runner 的 run：v1.11.0 的 NativeHTTPAdapter 只发 Content-Type，
**无 Authorization 头**（为无认证本地 LM Studio 端点设计），OpenRouter 裸 API 必 401。

权限边界（RULE-5 单向权限）：本脚本**只收集 reviewer 标记**，不回写被审文档。
审查者永不直接改写实现——防 answer corruption。

用法：
    python scripts/sft_review.py --target spec/distributed-sft/RESEARCH.md
    python scripts/sft_review.py --target X.md --out docs/reviews/X.review.md
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_KEY_FILE = r"D:\RPC\secrets\openrouter.key"
DEFAULT_BASE = "https://openrouter.ai/api/v1"
# 默认模型 = D:\RPC\secrets\openrouter.conf 的 model 键（裸 API 通用档，非 harness-only）
DEFAULT_MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"

SYSTEM = """你是一名严格的学术与工程审稿人，任务是**对抗性审查**一份按「Spec 驱动开发规范」产出的调研文档。
你的基座与文档作者**不同家族**，这正是本次审查的价值来源——请刻意质疑作者可能共享的盲区。

审查维度（逐条过，不要客气）：
1. **断言分级是否恰当**：标 A（事实类）的是否真有可核验来源？标 B（推断类）的推理链是否跳步？
   是否存在"证据全对但综合推理错"的形态 III 错误？
2. **结论是否被证据支撑**：有没有超出证据范围的断言？外部硬件（A100/Colab/NVIDIA 卡）的读数
   是否被不当地当作本集群（AMD gfx1151 / USB4 互联）的预期？
3. **降级与缺口是否被掩盖**：作者声称的"未取证 / 未验证"是否名副其实？有没有把推测写成事实？
4. **单源风险**：阻断性结论若只有一个来源，是否已声明？
5. **遗漏的替代解释**：作者排除某方案的理由，是否存在别的解释？

输出格式（严格遵守，每条一段）：
### 发现 N
- 位置：<章节号或引用原文片段>
- 级别：P1（阻断）/ P2（应修）/ P3（提示）
- 问题：<具体说清错在哪或弱在哪>
- 依据：<你凭什么这么说>

最后给一段「总评」：这份文档最可能误导读者的**一处**是什么。
★ 只标记问题，**不要改写文档**（审查者单向权限）。若某维度无问题，写"该维度未发现"，不要编造。"""

SYSTEM_DESIGN = """你是一名严格的架构评审人，任务是**对抗性审查**一份按「Spec 驱动开发规范」产出的**设计文档**。
你的基座与文档作者**不同家族**，这正是本次审查的价值来源——请刻意质疑作者可能共享的盲区。

审查维度（逐条过，不要客气）：
1. **决策是否有资格成立**：每个关键决策是否给了「被拒绝的替代方案 + 拒绝理由 + 承认的代价」三件？
   有没有"只说别人不好、不说自己贵在哪"的空否决？
2. **是否把未验证的前提当已验证**：设计依赖的事实里哪些还没实测？作者有没有用括号注或模糊措辞
   （"倾向"/"可能"）掩盖这一点？**否决一个方案需要资格**——证据不足时应写"未定"而非"不可行"。
3. **不变式是否可判**：每条 invariant 能否被机械或至少明确地判定违反？有没有写成愿望的？
4. **接口是否可实现**：签名、必填项、产物、回退点是否齐备？有没有依赖了上游并不存在的能力？
5. **归因扭曲**：作者是否因为某方案"优雅/省事"而给它找事后理由？是否把"我有这个工具"当成"这条路可行"？
6. **职责越界**：设计是否悄悄改了它声明"不管"的东西？

输出格式（严格遵守，每条一段）：
### 发现 N
- 位置：<章节号或引用原文片段>
- 级别：P1（阻断）/ P2（应修）/ P3（提示）
- 问题：<具体说清错在哪或弱在哪>
- 依据：<你凭什么这么说>

最后给一段「总评」：这份设计**最可能在实施阶段崩掉的一处**是什么。
★ 只标记问题，**不要改写文档**（审查者单向权限）。某维度无问题就写"该维度未发现"，不要编造。
★ 涉及具体硬件数值时**不要凭印象给规格**——不确定就写"需实测"，作者会自行核验。"""


def _system_for(mode: str) -> str:
    return SYSTEM_DESIGN if mode == "design" else SYSTEM


def read_key(path: str) -> str:
    p = Path(path)
    if not p.is_file():
        raise SystemExit(f"key 文件不存在: {path}")
    for line in p.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s and not s.startswith("#"):
            return s
    raise SystemExit(f"key 文件无有效行（全是注释？）: {path}")


def main() -> int:
    ap = argparse.ArgumentParser(prog="sft_review")
    ap.add_argument("--target", required=True)
    ap.add_argument("--mode", choices=("research", "design"), default="research",
                    help="被审文档类型（决定审查维度集）")
    ap.add_argument("--out", help="审查结果落盘路径（默认打印）")
    ap.add_argument("--model", default=os.environ.get("OR_MODEL", DEFAULT_MODEL))
    ap.add_argument("--base", default=os.environ.get("OR_BASE", DEFAULT_BASE))
    ap.add_argument("--key-file", default=os.environ.get("OR_KEY_FILE", DEFAULT_KEY_FILE))
    ap.add_argument("--max-tokens", type=int, default=4000)
    ap.add_argument("--timeout", type=int, default=300)
    a = ap.parse_args()

    doc = (ROOT / a.target).read_text(encoding="utf-8")
    key = read_key(a.key_file)
    user = (f"被审文档路径：{a.target}\n\n"
            f"以下是文档全文（{len(doc)} 字符）：\n\n---\n{doc}\n---\n\n"
            f"请按审查维度逐条给出发现。")

    payload = json.dumps({
        "model": a.model,
        "messages": [{"role": "system", "content": _system_for(a.mode)},
                     {"role": "user", "content": user}],
        "max_tokens": a.max_tokens,
        "temperature": 0.3,
    }).encode("utf-8")

    req = urllib.request.Request(
        a.base.rstrip("/") + "/chat/completions", data=payload,
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + key},
        method="POST")
    print(f"[review] model={a.model} target={a.target} bytes={len(doc)}", file=sys.stderr)
    try:
        with urllib.request.urlopen(req, timeout=a.timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"[review] HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:400]}",
              file=sys.stderr)
        return 1
    except Exception as e:  # noqa: BLE001
        print(f"[review] 失败: {type(e).__name__}: {e}", file=sys.stderr)
        return 1

    text = data["choices"][0]["message"]["content"]
    usage = data.get("usage") or {}
    header = (f"<!-- reviewer={a.model} provider=openrouter mode={a.mode} "
              f"target={a.target} tokens={usage.get('total_tokens', '?')} -->\n\n")
    out = header + text + "\n"
    if a.out:
        p = ROOT / a.out
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(out, encoding="utf-8")
        print(f"[review] 已写入 {a.out}（{len(text)} 字符，usage={usage}）", file=sys.stderr)
    else:
        print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
