#!/usr/bin/env python3
"""
Generate paper-aligned comparison artifacts from unified results.
Focus: Quantum vs MIQP-labeled classical baseline in rebalance-compare mode.
"""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "results" / "unified_train_test_compare.json"
OUT_CSV = ROOT / "results" / "paper_aligned_quantum_vs_miqp.csv"
OUT_MD = ROOT / "results" / "paper_aligned_quantum_vs_miqp.md"


def main() -> int:
    if not REPORT.exists():
        raise FileNotFoundError(f"Missing report: {REPORT}")

    data = json.loads(REPORT.read_text(encoding="utf-8"))
    rows = []

    for group_key, group_name in (("horizon_results", "horizon"), ("crash_results", "crash")):
        for scenario_name, rec in data.get(group_key, {}).items():
            if rec.get("status") != "ok":
                continue
            methods = rec.get("methods", {})
            q = methods.get("Quantum_NoRebalance", {})
            qr = methods.get("Quantum_Rebalanced", {})
            b = methods.get("MIQP", methods.get("Markowitz", {}))
            b_name = "MIQP" if "MIQP" in methods else ("Markowitz" if "Markowitz" in methods else "Unknown")

            rows.append(
                {
                    "group": group_name,
                    "scenario": scenario_name,
                    "quantum_no_rebalance_return": float(q.get("total_return", 0.0)),
                    "quantum_rebalanced_return": float(qr.get("total_return", 0.0)),
                    "baseline_method": b_name,
                    "baseline_return": float(b.get("total_return", 0.0)),
                    "qr_minus_baseline": float(qr.get("total_return", 0.0)) - float(b.get("total_return", 0.0)),
                    "winner_total_return": rec.get("winners", {}).get("best_total_return", ""),
                }
            )

    header = [
        "group",
        "scenario",
        "quantum_no_rebalance_return",
        "quantum_rebalanced_return",
        "baseline_method",
        "baseline_return",
        "qr_minus_baseline",
        "winner_total_return",
    ]
    lines = [",".join(header)]
    for r in rows:
        lines.append(
            ",".join(
                [
                    r["group"],
                    r["scenario"].replace(",", " "),
                    f"{r['quantum_no_rebalance_return']:.6f}",
                    f"{r['quantum_rebalanced_return']:.6f}",
                    r["baseline_method"],
                    f"{r['baseline_return']:.6f}",
                    f"{r['qr_minus_baseline']:.6f}",
                    str(r["winner_total_return"]),
                ]
            )
        )
    OUT_CSV.write_text("\n".join(lines), encoding="utf-8")

    md = [
        "# Paper-aligned Quantum vs MIQP Comparison",
        "",
        "| Group | Scenario | Quantum NoRebal | Quantum Rebal | Baseline | QR-Baseline | Winner |",
        "|---|---|---:|---:|---|---:|---|",
    ]
    for r in rows:
        md.append(
            f"| {r['group']} | {r['scenario']} | {r['quantum_no_rebalance_return']:.2f} | "
            f"{r['quantum_rebalanced_return']:.2f} | {r['baseline_method']} {r['baseline_return']:.2f} | "
            f"{r['qr_minus_baseline']:+.2f} | {r['winner_total_return']} |"
        )
    OUT_MD.write_text("\n".join(md), encoding="utf-8")

    print(f"Saved: {OUT_CSV}")
    print(f"Saved: {OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
