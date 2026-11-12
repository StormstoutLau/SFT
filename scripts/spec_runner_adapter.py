#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""D:\SFT 的 Spec_Runner 接入壳 —— 复制自 F:\Spec_Runner\templates\spec_runner_adapter.py v1.1

配置：RUNNER=F:\Spec_Runner\spec_runner.py（v1.0.0）/ PREFIX=sft / CWD=D:\SFT
GATES = 本仓四道校验器。

=== 与上游模板的唯一差异（差异就地登记，未改 gate 语义） ===
`_exec()` 注入 `SR_SESSIONS_DIR` 指向本仓 `tools\spec_runner\sessions\`。
为什么：v1.0.0 的 sessions 默认落 runner 自己仓内（`F:\Spec_Runner\sessions`），
而本仓的 `step_enforce.py` / `console_gen.py` 判据路径是 `<仓根>\tools\spec_runner\sessions\`
（沿用 Spec_Workflow 形态）。注入 env 使**事件流与产生它的仓同处**——否则 E1 证据
落在别的仓，本仓门禁看不见。runner 本体仍是零副本引用。

命令面：
  python scripts/spec_runner_adapter.py gates
  python scripts/spec_runner_adapter.py probe
  python scripts/spec_runner_adapter.py gate dc-validator
  python scripts/spec_runner_adapter.py replay --session <sid>
  python scripts/spec_runner_adapter.py dry-run gate m7-stats
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# ============================================================
# >>> 配置区 <<<
# ============================================================

RUNNER = r"D:\SFT\tools\spec_runner\spec_runner.py"
PREFIX = "sft"
CWD = r"D:\SFT"
SESSIONS = r"D:\SFT\tools\spec_runner\sessions"

GATES = {
    "probe": "echo SFT-adapter OK",
    "dc-validator": "python scripts/dc_validator.py --check-all",
    "m7-stats": "python scripts/m7_stats.py",
    "repo-stats": "python scripts/repo_stats.py",
    "degradation-gate": "python scripts/degradation_gate.py",
    "step-enforce": "python scripts/step_enforce.py",
}

ENDPOINT = os.environ.get("SR_ENDPOINT") or ""
MODEL = os.environ.get("SR_MODEL") or ""
PROVIDER = os.environ.get("SR_PROVIDER") or ""

# ============================================================
# >>> 以下无需修改 <<<
# ============================================================

BASE = Path(__file__).resolve().parent
DEFAULT_CWD = CWD or str(BASE.parent)


def _runner_cmd() -> list:
    return [sys.executable, RUNNER]


def _session_for(name: str) -> str:
    return f"{PREFIX}-{name}-{datetime.now():%Y%m%d}"


def _build_gate_cmd(args, name: str) -> list:
    if name not in GATES:
        print(f"gate: unknown '{name}'——可用: {', '.join(GATES)}", file=sys.stderr)
        sys.exit(2)
    return ([*_runner_cmd(), "gate", "--name", name, "--cmd", GATES[name],
             "--session", args.session or _session_for(name)] +
            (["--cwd", DEFAULT_CWD]))


def _build_run_cmd(args) -> list:
    sid = args.session or f"{PREFIX}-run-{datetime.now():%Y%m%d}"
    cmd = [*_runner_cmd(), "run", "--task", args.task, "--session", sid]
    if args.resume:
        cmd.append("--resume")
    for g in args.require_gate:
        cmd += ["--require-gate", g]
    if args.prompt:
        cmd += ["--prompt", args.prompt]
    if args.prompt_file:
        cmd += ["--prompt-file", args.prompt_file]
    for flag, val in (("--endpoint", ENDPOINT), ("--model", MODEL),
                      ("--provider", PROVIDER)):
        if val:
            cmd += [flag, val]
    return cmd


def _exec(cmd: list) -> int:
    print("+", " ".join(cmd))
    env = dict(os.environ, SR_SESSIONS_DIR=SESSIONS)
    try:
        Path(SESSIONS).mkdir(parents=True, exist_ok=True)
        proc = subprocess.run(cmd, cwd=DEFAULT_CWD, env=env, text=True,
                              encoding="utf-8", errors="replace")
    except FileNotFoundError:
        print(f"exec: 找不到 {cmd[1]}——请检查 RUNNER 配置", file=sys.stderr)
        return 127
    return proc.returncode


def _action_cmd(args) -> list:
    if args.cmd == "gate":
        return _build_gate_cmd(args, args.name)
    if args.cmd == "run":
        return _build_run_cmd(args)
    if args.cmd == "gates":
        return ["(列出 GATES 表)"]
    if args.cmd == "probe":
        probe = argparse.Namespace(cmd="gate", name="probe", session=None,
                                   resume=False)
        return _build_gate_cmd(probe, "probe")
    cmd = [*_runner_cmd(), args.cmd]
    for flag, val in (("--session", getattr(args, "session", None)),
                      ("--seq", getattr(args, "seq_from", None)),
                      ("--new", getattr(args, "new", None))):
        if val:
            cmd += [flag, str(val)]
    return cmd


def _run(argv_override=None) -> int:
    p = argparse.ArgumentParser(prog="spec_runner_adapter",
                                description="D:\\SFT 的 Spec_Runner 接入壳",
                                add_help=True)
    sub = p.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("gate", help="从 GATES 表执行门禁（exit 透传）")
    g.add_argument("name")
    g.add_argument("--session")
    g.add_argument("--resume", action="store_true")

    sub.add_parser("gates", help="列出可用门禁")

    r = sub.add_parser("run", help="透传 Spec_Runner run")
    r.add_argument("--task", required=True)
    r.add_argument("--session")
    r.add_argument("--resume", action="store_true")
    r.add_argument("--require-gate", action="append", default=[])
    r.add_argument("--prompt")
    r.add_argument("--prompt-file")

    for name in ("status", "replay"):
        sp = sub.add_parser(name)
        sp.add_argument("--session")

    f = sub.add_parser("fork")
    f.add_argument("--session")
    f.add_argument("--seq", dest="seq_from", type=int)
    f.add_argument("--new")

    sub.add_parser("probe", help="接入自检（echo 探针 gate）")

    d = sub.add_parser("dry-run", help="打印将执行的命令，不实际运行")
    d.add_argument("inner", nargs=argparse.REMAINDER)

    args = p.parse_args(argv_override)

    if args.cmd == "dry-run":
        inner = args.inner or ["gates"]
        inner_argv = inner[1:] if inner[0] == "--" else inner
        inner_args = p.parse_args(inner_argv)
        print("DRY-RUN:", " ".join(_action_cmd(inner_args)))
        return 0

    if args.cmd == "gates":
        print("\n".join(f"{k:20s} {v}" for k, v in GATES.items()))
        return 0
    if args.cmd == "probe":
        return _exec_gate(argparse.Namespace(name="probe", session=None))
    if args.cmd == "gate":
        return _exec_gate(args)
    if args.cmd == "run":
        return _exec_run(args)
    cmd = [*_runner_cmd(), args.cmd]
    for flag, val in (("--session", getattr(args, "session", None)),
                      ("--seq", getattr(args, "seq_from", None)),
                      ("--new", getattr(args, "new", None))):
        if val:
            cmd += [flag, str(val)]
    return _exec(cmd)


def _exec_gate(args) -> int:
    return _exec(_build_gate_cmd(args, args.name))


def _exec_run(args) -> int:
    return _exec(_build_run_cmd(args))


if __name__ == "__main__":
    sys.exit(_run())
