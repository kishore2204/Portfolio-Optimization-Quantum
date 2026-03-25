#!/usr/bin/env python3
"""
Create paper-style no-rebalance comparison artifact:
Quantum vs Classical baseline (and Greedy shown for reference).
"""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "results" / "unified_train_test_compare.json"
OUT_CSV = ROOT / "results" / "paper_no_rebalance_quantum_vs_classical.csv"
OUT_MD = ROOT / "results" / "paper_no_rebalance_quantum_vs_classical.md"


def main() -> int:
    data = json.loads(REPORT.read_text(encoding="utf-8"))

    rows = []
    for group_key, group_name in (("horizon_results", "horizon"), ("crash_results", "crash")):
        for scenario_name, rec in data.get(group_key, {}).items():
            if rec.get("status") != "ok":
                continue
            m = rec.get("methods", {})
            q = m.get("Quantum", {})
            g = m.get("Greedy", {})
            c = m.get("Classical", {})
            rows.append(
                {
                    "group": group_name,
                    "scenario": scenario_name,
                    "quantum_return": float(q.get("total_return", 0.0)),
                    "classical_return": float(c.get("total_return", 0.0)),
                    "greedy_return": float(g.get("total_return", 0.0)),
                    "q_minus_classical": float(q.get("total_return", 0.0)) - float(c.get("total_return", 0.0)),
                    "winner_total_return": rec.get("winners", {}).get("best_total_return", ""),
                }
            )

    header = [
        "group",
        "scenario",
        "quantum_return",
        "classical_return",
        "greedy_return",
        "q_minus_classical",
        "winner_total_return",
    ]
    lines = [",".join(header)]
    for r in rows:
        lines.append(
            ",".join(
                [
                    r["group"],
                    r["scenario"].replace(",", " "),
                    f"{r['quantum_return']:.6f}",
                    f"{r['classical_return']:.6f}",
                    f"{r['greedy_return']:.6f}",
                    f"{r['q_minus_classical']:.6f}",
                    str(r["winner_total_return"]),
                ]
            )
        )
    OUT_CSV.write_text("\n".join(lines), encoding="utf-8")

    md = [
        "# Paper-style No-Rebalance Comparison",
        "",
        "| Group | Scenario | Quantum | Classical | Greedy | Q-Classical | Winner |",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    for r in rows:
        md.append(
            f"| {r['group']} | {r['scenario']} | {r['quantum_return']:.2f} | {r['classical_return']:.2f} | "
            f"{r['greedy_return']:.2f} | {r['q_minus_classical']:+.2f} | {r['winner_total_return']} |"
        )
    OUT_MD.write_text("\n".join(md), encoding="utf-8")

    print(f"Saved: {OUT_CSV}")
    print(f"Saved: {OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
