#!/usr/bin/env python3
"""
Run one-pass rebalance tuning for three objectives:
1) Max return focus
2) Max Sharpe focus
3) Max drawdown protection focus

Outputs:
- results/rebalance_profile_tuning_summary.csv
- results/rebalance_profile_tuning_summary.json
- results/unified_train_test_compare_<profile>.json
"""

from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path
from statistics import mean


ROOT = Path(__file__).resolve().parent.parent
BASE_CONFIG = ROOT / "config" / "unified_compare_config.json"
RESULTS_DIR = ROOT / "results"


def load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, payload: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def collect_scenario_rows(report: dict):
    rows = []
    for grp_key in ("horizon_results", "crash_results"):
        group = "horizon" if grp_key == "horizon_results" else "crash"
        for scenario, payload in report.get(grp_key, {}).items():
            if payload.get("status") != "ok":
                continue
            methods = payload.get("methods", {})
            q = methods.get("Quantum_NoRebalance", {})
            qr = methods.get("Quantum_Rebalanced", {})
            c = methods.get("Markowitz", methods.get("Greedy", {}))
            if not qr:
                continue
            rows.append(
                {
                    "group": group,
                    "scenario": scenario,
                    "q_return": float(q.get("total_return", 0.0)),
                    "qr_return": float(qr.get("total_return", 0.0)),
                    "c_return": float(c.get("total_return", 0.0)),
                    "q_sharpe": float(q.get("sharpe", 0.0)),
                    "qr_sharpe": float(qr.get("sharpe", 0.0)),
                    "c_sharpe": float(c.get("sharpe", 0.0)),
                    "q_mdd": float(q.get("max_drawdown", 0.0)),
                    "qr_mdd": float(qr.get("max_drawdown", 0.0)),
                    "c_mdd": float(c.get("max_drawdown", 0.0)),
                    "rebalances": int(qr.get("rebalances_applied", 0)),
                }
            )
    return rows


def summarize_profile(profile_name: str, report: dict) -> dict:
    rows = collect_scenario_rows(report)
    if not rows:
        return {
            "profile": profile_name,
            "scenarios": 0,
        }

    qr_returns = [r["qr_return"] for r in rows]
    qr_sharpes = [r["qr_sharpe"] for r in rows]
    qr_mdds = [r["qr_mdd"] for r in rows]

    q_returns = [r["q_return"] for r in rows]
    c_returns = [r["c_return"] for r in rows]

    qr_vs_q_return_delta = [r["qr_return"] - r["q_return"] for r in rows]
    qr_vs_c_return_delta = [r["qr_return"] - r["c_return"] for r in rows]

    wins_vs_q = sum(1 for d in qr_vs_q_return_delta if d > 0)
    wins_vs_c = sum(1 for d in qr_vs_c_return_delta if d > 0)

    return {
        "profile": profile_name,
        "scenarios": len(rows),
        "avg_qr_return": mean(qr_returns),
        "avg_qr_sharpe": mean(qr_sharpes),
        "avg_qr_max_drawdown": mean(qr_mdds),
        "avg_q_return": mean(q_returns),
        "avg_c_return": mean(c_returns),
        "avg_qr_minus_q_return": mean(qr_vs_q_return_delta),
        "avg_qr_minus_c_return": mean(qr_vs_c_return_delta),
        "wins_qr_vs_q_count": wins_vs_q,
        "wins_qr_vs_c_count": wins_vs_c,
        "avg_rebalances": mean([r["rebalances"] for r in rows]),
    }


def to_csv(summary_rows: list[dict], out_path: Path) -> None:
    cols = [
        "profile",
        "scenarios",
        "avg_qr_return",
        "avg_qr_sharpe",
        "avg_qr_max_drawdown",
        "avg_q_return",
        "avg_c_return",
        "avg_qr_minus_q_return",
        "avg_qr_minus_c_return",
        "wins_qr_vs_q_count",
        "wins_qr_vs_c_count",
        "avg_rebalances",
    ]
    lines = [",".join(cols)]
    for r in summary_rows:
        vals = []
        for c in cols:
            v = r.get(c, "")
            if isinstance(v, float):
                vals.append(f"{v:.6f}")
            else:
                vals.append(str(v))
        lines.append(",".join(vals))
    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    RESULTS_DIR.mkdir(exist_ok=True)
    base_cfg = load_json(BASE_CONFIG)

    profiles = {
        "max_return": {
            "rebalance_sell_count": 1,
            "rebalance_underperformer_threshold_annualized": -0.05,
            "rebalance_max_turnover": 0.45,
            "replacement_min_annualized_return": -0.02,
            "max_weight": 0.45,
        },
        "max_sharpe": {
            "rebalance_sell_count": 1,
            "rebalance_underperformer_threshold_annualized": 0.00,
            "rebalance_max_turnover": 0.30,
            "replacement_min_annualized_return": 0.02,
            "max_weight": 0.35,
        },
        "max_drawdown": {
            "rebalance_sell_count": 1,
            "rebalance_underperformer_threshold_annualized": 0.01,
            "rebalance_max_turnover": 0.20,
            "replacement_min_annualized_return": 0.01,
            "max_weight": 0.25,
        },
    }

    summary_rows = []

    for profile_name, patch in profiles.items():
        cfg = copy.deepcopy(base_cfg)
        w = cfg.setdefault("weight_optimization", {})
        for k, v in patch.items():
            w[k] = v

        tmp_cfg = RESULTS_DIR / f"_tmp_rebalance_profile_{profile_name}.json"
        write_json(tmp_cfg, cfg)

        cmd = [
            sys.executable,
            str(ROOT / "unified_train_test_compare.py"),
            "--config",
            str(tmp_cfg),
            "--only",
            "all",
            "--enable-rebalance-compare",
            "--rebalance-frequency",
            "quarterly",
        ]

        print(f"\n[RUN] {profile_name}")
        proc = subprocess.run(cmd, cwd=str(ROOT), check=False)
        if proc.returncode != 0:
            print(f"[WARN] Profile failed: {profile_name} (exit={proc.returncode})")
            continue

        report_path = RESULTS_DIR / "unified_train_test_compare.json"
        if not report_path.exists():
            print(f"[WARN] Missing report for {profile_name}")
            continue

        report = load_json(report_path)
        profile_report_out = RESULTS_DIR / f"unified_train_test_compare_{profile_name}.json"
        write_json(profile_report_out, report)

        summary = summarize_profile(profile_name, report)
        summary_rows.append(summary)

    # cleanup temp configs
    for p in RESULTS_DIR.glob("_tmp_rebalance_profile_*.json"):
        try:
            p.unlink()
        except Exception:
            pass

    summary_json = RESULTS_DIR / "rebalance_profile_tuning_summary.json"
    summary_csv = RESULTS_DIR / "rebalance_profile_tuning_summary.csv"
    write_json(summary_json, {"profiles": summary_rows})
    to_csv(summary_rows, summary_csv)

    if summary_rows:
        best_return = max(summary_rows, key=lambda r: r.get("avg_qr_return", float("-inf")))["profile"]
        best_sharpe = max(summary_rows, key=lambda r: r.get("avg_qr_sharpe", float("-inf")))["profile"]
        best_mdd = max(summary_rows, key=lambda r: r.get("avg_qr_max_drawdown", float("-inf")))["profile"]
        print("\n[WINNERS]")
        print(f"best_return={best_return}")
        print(f"best_sharpe={best_sharpe}")
        print(f"best_drawdown={best_mdd}")

    print(f"\nSaved: {summary_csv}")
    print(f"Saved: {summary_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
