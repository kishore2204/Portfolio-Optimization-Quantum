#!/usr/bin/env python3
"""
Master runner for Portfolio Optimization Quantum.

Runs in order:
1) core phase pipeline
2) unified horizon comparison
3) unified crash comparison

Writes a run summary markdown to results/final_run_summary.md.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def run_step(step_name: str, cmd: list[str], cwd: Path) -> tuple[bool, int]:
    print("\n" + "=" * 90)
    print(f"RUNNING: {step_name}")
    print("=" * 90)
    print("Command:", " ".join(cmd))

    proc = subprocess.run(cmd, cwd=str(cwd), check=False)
    ok = proc.returncode == 0

    status = "SUCCESS" if ok else "FAILED"
    print(f"[{status}] {step_name} (exit={proc.returncode})")
    return ok, proc.returncode


def write_summary(output_path: Path, rows: list[dict], generated_files: list[Path]) -> None:
    lines = []
    lines.append("# Final Run Summary")
    lines.append("")
    lines.append(f"Generated at: {datetime.now().isoformat(timespec='seconds')}")
    lines.append("")
    lines.append("## Step Status")
    lines.append("")
    lines.append("| Step | Status | Exit Code |")
    lines.append("|---|---|---:|")
    for row in rows:
        lines.append(f"| {row['step']} | {row['status']} | {row['code']} |")

    lines.append("")
    lines.append("## Key Output Files")
    lines.append("")
    for p in generated_files:
        mark = "OK" if p.exists() else "MISSING"
        lines.append(f"- {mark} - {p.as_posix()}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run full Portfolio Optimization Quantum flow")
    parser.add_argument("--python", default=sys.executable, help="Python executable")
    parser.add_argument("--skip-core", action="store_true", help="Skip core phase pipeline")
    parser.add_argument("--skip-horizon", action="store_true", help="Skip horizon comparison")
    parser.add_argument("--skip-crash", action="store_true", help="Skip crash comparison")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(__file__).resolve().parent

    rows = []
    overall_ok = True

    if not args.skip_core:
        ok, code = run_step(
            "Core Phase Pipeline",
            [args.python, "run_portfolio_optimization_quantum.py"],
            root,
        )
        rows.append({"step": "core_phase_pipeline", "status": "SUCCESS" if ok else "FAILED", "code": code})
        overall_ok = overall_ok and ok

    if not args.skip_horizon:
        ok, code = run_step(
            "Unified Horizon Comparison",
            [args.python, "unified_train_test_compare.py", "--only", "horizon"],
            root,
        )
        rows.append({"step": "unified_horizon", "status": "SUCCESS" if ok else "FAILED", "code": code})
        overall_ok = overall_ok and ok

    if not args.skip_crash:
        ok, code = run_step(
            "Unified Crash Comparison",
            [args.python, "unified_train_test_compare.py", "--only", "crash"],
            root,
        )
        rows.append({"step": "unified_crash", "status": "SUCCESS" if ok else "FAILED", "code": code})
        overall_ok = overall_ok and ok

    generated_files = [
        root / "results" / "strategy_comparison.json",
        root / "results" / "strategy_comparison.png",
        root / "results" / "unified_train_test_compare.json",
    ]

    summary_path = root / "results" / "final_run_summary.md"
    write_summary(summary_path, rows, generated_files)

    print("\n" + "=" * 90)
    print(f"Summary written: {summary_path}")
    print("=" * 90)

    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
