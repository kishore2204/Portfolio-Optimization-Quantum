#!/usr/bin/env python3
"""
Ablation tests for quantum-inspired enhancements.

Runs one-change-at-a-time variants and compares against baseline using:
- Avg scenario Quantum_Rebalanced return / Sharpe / max drawdown
- Avg turnover and total transaction cost
- Bootstrap 95% CI for avg return delta vs baseline

Outputs:
- results/quantum_ablation_summary.csv
- results/quantum_ablation_summary.json
- results/unified_train_test_compare_ablation_<variant>.json
"""

from __future__ import annotations

import copy
import json
import random
import subprocess
import sys
from pathlib import Path
from statistics import mean


ROOT = Path(__file__).resolve().parent.parent
BASE_CONFIG = ROOT / "config" / "unified_compare_config.json"
RESULTS = ROOT / "results"


def load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def scenario_rows(report: dict):
    rows = []
    for grp in ("horizon_results", "crash_results"):
        for name, rec in report.get(grp, {}).items():
            if rec.get("status") != "ok":
                continue
            m = rec.get("methods", {})
            qr = m.get("Quantum_Rebalanced")
            q = m.get("Quantum_NoRebalance")
            c = m.get("Markowitz", m.get("Greedy"))
            if not qr:
                continue
            rows.append(
                {
                    "scenario": name,
                    "qr_return": float(qr.get("total_return", 0.0)),
                    "qr_sharpe": float(qr.get("sharpe", 0.0)),
                    "qr_mdd": float(qr.get("max_drawdown", 0.0)),
                    "qr_turnover": float(qr.get("avg_turnover_per_rebalance", 0.0)),
                    "qr_tx_cost": float(qr.get("total_transaction_cost", 0.0)),
                    "q_return": float((q or {}).get("total_return", 0.0)),
                    "c_return": float((c or {}).get("total_return", 0.0)),
                }
            )
    return rows


def bootstrap_ci_mean(deltas: list[float], n_boot: int = 2000, seed: int = 7):
    if not deltas:
        return (0.0, 0.0)
    rng = random.Random(seed)
    n = len(deltas)
    means = []
    for _ in range(n_boot):
        sample = [deltas[rng.randrange(n)] for _ in range(n)]
        means.append(mean(sample))
    means.sort()
    lo = means[int(0.025 * (n_boot - 1))]
    hi = means[int(0.975 * (n_boot - 1))]
    return (float(lo), float(hi))


def apply_patch_dict(cfg: dict, patch: dict) -> dict:
    out = copy.deepcopy(cfg)
    for section, vals in patch.items():
        obj = out.setdefault(section, {})
        for k, v in vals.items():
            obj[k] = v
    return out


def run_variant(name: str, cfg: dict) -> dict | None:
    RESULTS.mkdir(exist_ok=True)
    cfg_path = RESULTS / f"_tmp_ablation_{name}.json"
    write_json(cfg_path, cfg)

    cmd = [
        sys.executable,
        str(ROOT / "unified_train_test_compare.py"),
        "--config",
        str(cfg_path),
        "--only",
        "all",
        "--enable-rebalance-compare",
        "--rebalance-frequency",
        "quarterly",
    ]

    print(f"\n[ABLATION] {name}")
    proc = subprocess.run(cmd, cwd=str(ROOT), check=False)
    if proc.returncode != 0:
        print(f"[WARN] variant failed: {name}")
        return None

    report_path = RESULTS / "unified_train_test_compare.json"
    if not report_path.exists():
        return None

    report = load_json(report_path)
    write_json(RESULTS / f"unified_train_test_compare_ablation_{name}.json", report)
    return report


def main() -> int:
    base = load_json(BASE_CONFIG)

    # Standardize baseline: all experimental quantum features off.
    baseline_patch = {
        "qubo": {
            "regime_conditional_enabled": False,
            "turnover_aware_enabled": False,
            "turnover_penalty": 0.0,
            "uncertainty_aware_enabled": False,
            "instability_gamma": 0.0,
            "mean_shrinkage": 0.0,
            "ensemble_confidence_threshold": 0.0,
            "warm_start_enabled": False,
            "path_relinking_enabled": False,
            "path_relinking_passes": 1,
            "adaptive_turnover_cap_enabled": False,
        }
    }

    variants = {
        "baseline": baseline_patch,
        "regime_conditional": {
            "qubo": {
                **baseline_patch["qubo"],
                "regime_conditional_enabled": True,
                "trend_risk_aversion_mult": 0.9,
                "trend_downside_beta_mult": 0.8,
                "trend_lambda_scale_mult": 0.9,
                "unstable_risk_aversion_mult": 1.2,
                "unstable_downside_beta_mult": 1.3,
                "unstable_lambda_scale_mult": 1.1,
            }
        },
        "turnover_aware_qubo": {
            "qubo": {
                **baseline_patch["qubo"],
                "turnover_aware_enabled": True,
                "turnover_penalty": 0.05,
            }
        },
        "robust_qubo": {
            "qubo": {
                **baseline_patch["qubo"],
                "uncertainty_aware_enabled": True,
                "instability_gamma": 0.06,
                "mean_shrinkage": 0.20,
            }
        },
        "ensemble_confidence": {
            "qubo": {
                **baseline_patch["qubo"],
                "ensemble_confidence_threshold": 0.67,
            }
        },
        "warmstart_pathrelink": {
            "qubo": {
                **baseline_patch["qubo"],
                "turnover_aware_enabled": True,
                "turnover_penalty": 0.03,
                "warm_start_enabled": True,
                "path_relinking_enabled": True,
                "path_relinking_passes": 2,
            }
        },
        "adaptive_turnover_cap": {
            "qubo": {
                **baseline_patch["qubo"],
                "adaptive_turnover_cap_enabled": True,
                "turnover_cap_trend": 0.45,
                "turnover_cap_neutral": 0.30,
                "turnover_cap_unstable": 0.18,
            }
        },
        "combined_all": {
            "qubo": {
                "regime_conditional_enabled": True,
                "trend_risk_aversion_mult": 0.9,
                "trend_downside_beta_mult": 0.8,
                "trend_lambda_scale_mult": 0.9,
                "unstable_risk_aversion_mult": 1.2,
                "unstable_downside_beta_mult": 1.3,
                "unstable_lambda_scale_mult": 1.1,
                "turnover_aware_enabled": True,
                "turnover_penalty": 0.04,
                "uncertainty_aware_enabled": True,
                "instability_gamma": 0.05,
                "mean_shrinkage": 0.15,
                "ensemble_confidence_threshold": 0.67,
                "warm_start_enabled": True,
                "path_relinking_enabled": True,
                "path_relinking_passes": 2,
                "adaptive_turnover_cap_enabled": True,
                "turnover_cap_trend": 0.45,
                "turnover_cap_neutral": 0.30,
                "turnover_cap_unstable": 0.18,
            }
        },
    }

    reports = {}
    for name, patch in variants.items():
        cfg = apply_patch_dict(base, patch)
        rep = run_variant(name, cfg)
        if rep is not None:
            reports[name] = rep

    # Cleanup temp configs.
    for p in RESULTS.glob("_tmp_ablation_*.json"):
        try:
            p.unlink()
        except Exception:
            pass

    if "baseline" not in reports:
        print("Baseline run failed; cannot compute ablation deltas.")
        return 1

    base_rows = scenario_rows(reports["baseline"])
    base_by_s = {r["scenario"]: r for r in base_rows}

    summary = []
    for name, rep in reports.items():
        rows = scenario_rows(rep)
        if not rows:
            continue

        ret = [r["qr_return"] for r in rows]
        shp = [r["qr_sharpe"] for r in rows]
        mdd = [r["qr_mdd"] for r in rows]
        turn = [r["qr_turnover"] for r in rows]
        txc = [r["qr_tx_cost"] for r in rows]

        deltas = []
        for r in rows:
            b = base_by_s.get(r["scenario"])
            if b is not None:
                deltas.append(r["qr_return"] - b["qr_return"])

        ci_lo, ci_hi = bootstrap_ci_mean(deltas)
        summary.append(
            {
                "variant": name,
                "scenarios": len(rows),
                "avg_qr_return": mean(ret),
                "avg_qr_sharpe": mean(shp),
                "avg_qr_max_drawdown": mean(mdd),
                "avg_qr_turnover": mean(turn),
                "avg_qr_tx_cost": mean(txc),
                "avg_return_delta_vs_baseline": mean(deltas) if deltas else 0.0,
                "avg_return_delta_ci95_lo": ci_lo,
                "avg_return_delta_ci95_hi": ci_hi,
            }
        )

    summary.sort(key=lambda x: x["avg_qr_return"], reverse=True)

    out_json = RESULTS / "quantum_ablation_summary.json"
    out_csv = RESULTS / "quantum_ablation_summary.csv"
    write_json(out_json, {"summary": summary})

    cols = [
        "variant",
        "scenarios",
        "avg_qr_return",
        "avg_qr_sharpe",
        "avg_qr_max_drawdown",
        "avg_qr_turnover",
        "avg_qr_tx_cost",
        "avg_return_delta_vs_baseline",
        "avg_return_delta_ci95_lo",
        "avg_return_delta_ci95_hi",
    ]
    lines = [",".join(cols)]
    for r in summary:
        row = []
        for c in cols:
            v = r.get(c, "")
            if isinstance(v, float):
                row.append(f"{v:.6f}")
            else:
                row.append(str(v))
        lines.append(",".join(row))
    out_csv.write_text("\n".join(lines), encoding="utf-8")

    print(f"\nSaved: {out_csv}")
    print(f"Saved: {out_json}")
    if summary:
        print("Top variant by avg_qr_return:", summary[0]["variant"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
