#!/usr/bin/env python3
"""
Unified horizon and crash evaluator using copied modules from both source projects.

Methods compared in every scenario:
- Quantum (QUBO + simulated annealing)
- Greedy (top Sharpe)
- Classical (return/variance score)
"""

from __future__ import annotations

import argparse
from datetime import datetime
import importlib.util
import json
from pathlib import Path
from typing import Dict, List, Set

import pandas as pd

import phase_08_crash_and_regime_evaluation as crash_mod


def load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_nifty100_symbols(base_dir: Path, sectors_rel_path: str) -> Set[str]:
    sectors_path = (base_dir / sectors_rel_path).resolve()
    if not sectors_path.exists():
        raise FileNotFoundError(f"NIFTY100 sectors file not found: {sectors_path}")

    data = load_json(sectors_path)
    groups = data.get("NIFTY_100_STOCKS", {})
    symbols: Set[str] = set()
    for stocks in groups.values():
        symbols.update(stocks)
    return symbols


def apply_universe_filter(prices_df: pd.DataFrame, mode: str, allowed_symbols: Set[str] | None = None):
    asset_cols = [c for c in prices_df.columns if c != "Date"]
    raw_assets = len(asset_cols)

    if mode == "full_universe":
        return prices_df, {
            "raw_assets": raw_assets,
            "filtered_assets": raw_assets,
            "dropped_assets": 0,
        }

    if mode != "nifty100_only":
        raise ValueError(f"Unknown universe mode: {mode}")

    if not allowed_symbols:
        raise ValueError("nifty100_only mode requested, but no NIFTY100 symbols were provided")

    kept_assets = [c for c in asset_cols if c in allowed_symbols]
    if not kept_assets:
        raise ValueError("NIFTY100 filter resulted in zero matching assets in selected dataset")

    filtered_df = prices_df[["Date"] + kept_assets].copy()
    return filtered_df, {
        "raw_assets": raw_assets,
        "filtered_assets": len(kept_assets),
        "dropped_assets": raw_assets - len(kept_assets),
    }


def resolve_k_stocks(base_dir: Path, eval_cfg: dict, cli_k: int | None) -> int:
    if cli_k is not None:
        return int(cli_k)

    mode = str(eval_cfg.get("k_mode", "fixed"))
    fallback = int(eval_cfg.get("k_stocks", 10))
    k_min = int(eval_cfg.get("k_min", 1))
    k_max = int(eval_cfg.get("k_max", 9999))

    if mode == "auto_from_phase2_if_available":
        card_path = base_dir / "portfolios" / "cardinality_analysis.json"
        if card_path.exists():
            try:
                data = load_json(card_path)
                derived = int(data.get("K_optimal", fallback))
                return max(k_min, min(k_max, derived))
            except Exception:
                return max(k_min, min(k_max, fallback))

    return max(k_min, min(k_max, fallback))


def _load_eq7_cardinality_module(base_dir: Path):
    module_path = base_dir / "phase_02_cardinality_determination.py"
    spec = importlib.util.spec_from_file_location("phase2_cardinality", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def derive_scenario_k_from_train_window(
    base_dir: Path,
    prices_df: pd.DataFrame,
    scenario_cfg: dict,
    eligible_stocks: List[str],
    eval_cfg: dict,
    fallback_k: int,
) -> int:
    dynamic_cfg = eval_cfg.get("dynamic_k", {})
    if not bool(dynamic_cfg.get("enabled", False)):
        return fallback_k

    mode = str(dynamic_cfg.get("mode", "eq7_train_window"))
    if mode != "eq7_train_window":
        return fallback_k

    k_min = int(dynamic_cfg.get("k_min", eval_cfg.get("k_min", 1)))
    k_max = int(dynamic_cfg.get("k_max", eval_cfg.get("k_max", 9999)))
    rf_rate = float(dynamic_cfg.get("risk_free_rate", 0.06))

    train_mask = (prices_df["Date"] >= scenario_cfg["train_start"]) & (prices_df["Date"] <= scenario_cfg["train_end"])
    train_df = prices_df.loc[train_mask, ["Date"] + eligible_stocks].copy()
    if len(train_df) < 30:
        return max(k_min, min(k_max, fallback_k))

    returns = train_df[eligible_stocks].ffill().bfill().pct_change().dropna()
    if returns.empty:
        return max(k_min, min(k_max, fallback_k))

    mean_returns = returns.mean().values * 252
    cov_matrix = returns.cov().values * 252

    try:
        phase2 = _load_eq7_cardinality_module(base_dir)
        k_derived, _ = phase2.determine_optimal_cardinality(
            mean_returns,
            cov_matrix,
            rf_rate=rf_rate,
            verbose=False,
        )
    except Exception:
        k_derived = fallback_k

    k_derived = int(max(k_min, min(k_max, int(k_derived))))
    k_derived = min(k_derived, len(eligible_stocks))
    return max(1, k_derived)


def profile_dataset(path: Path):
    if not path.exists():
        return None
    try:
        df = pd.read_csv(path, parse_dates=["Date"])
    except Exception:
        return None
    if "Date" not in df.columns or len(df) == 0 or len(df.columns) < 3:
        return None
    df = df.sort_values("Date")
    return {
        "path": str(path.resolve()),
        "rows": int(len(df)),
        "assets": int(len(df.columns) - 1),
        "start": str(df["Date"].min().date()),
        "end": str(df["Date"].max().date()),
        "end_ts": pd.to_datetime(df["Date"].max()),
    }


def choose_best_dataset(base_dir: Path, candidates: List[str]):
    profiles = []
    for rel in candidates:
        prof = profile_dataset((base_dir / rel).resolve())
        if prof:
            profiles.append(prof)

    if not profiles:
        raise FileNotFoundError("No valid dataset found in configured candidates")

    profiles.sort(key=lambda x: (x["end_ts"], x["rows"], x["assets"]), reverse=True)
    return profiles[0]


def build_horizon_scenarios(
    end_ts,
    horizon_months: List[int],
    train_map: Dict[str, int],
    train_window_mode: str = "rolling",
    dataset_start_ts=None,
):
    scenarios = {}
    dataset_start_norm = pd.to_datetime(dataset_start_ts).normalize() if dataset_start_ts is not None else None

    for test_m in horizon_months:
        train_m = int(train_map.get(str(test_m), test_m))
        test_end = pd.to_datetime(end_ts)
        test_start = (test_end - pd.DateOffset(months=test_m) + pd.Timedelta(days=1)).normalize()
        train_end = (test_start - pd.Timedelta(days=1)).normalize()

        if train_window_mode == "expanding_from_start":
            if dataset_start_norm is None:
                raise ValueError("dataset_start_ts is required when train_window_mode=expanding_from_start")
            train_start = dataset_start_norm
            name = f"Horizon_{test_m}M_Train_Expanding"
            description = f"Test={test_m}M, Train=expanding from dataset start"
        else:
            train_start = (train_end - pd.DateOffset(months=train_m) + pd.Timedelta(days=1)).normalize()
            name = f"Horizon_{test_m}M_Train_{train_m}M"
            description = f"Test={test_m}M, Train={train_m}M ending at latest date"

        scenarios[f"Horizon_{test_m}M_Train_{train_m}M"] = {
            "train_start": str(train_start.date()),
            "train_end": str(train_end.date()),
            "test_start": str(test_start.date()),
            "test_end": str(test_end.date()),
            "description": description
        }
        if train_window_mode == "expanding_from_start":
            scenarios[name] = scenarios.pop(f"Horizon_{test_m}M_Train_{train_m}M")
    return scenarios


def winner_by_metric(methods: Dict[str, dict], metric: str, maximize: bool = True):
    vals = [(k, v.get(metric)) for k, v in methods.items() if v and metric in v]
    if not vals:
        return None
    return (max(vals, key=lambda x: x[1]) if maximize else min(vals, key=lambda x: x[1]))[0]


def budget_partition_summary(weight_map: Dict[str, float], budget: float) -> dict:
    if budget <= 0:
        return {
            "budget": float(budget),
            "invested": 0.0,
            "cash": 0.0,
            "top_allocations": [],
        }

    allocations = {k: float(v) * float(budget) for k, v in weight_map.items()}
    invested = float(sum(allocations.values()))
    cash = float(budget - invested)
    top = sorted(allocations.items(), key=lambda x: x[1], reverse=True)[:5]

    return {
        "budget": float(budget),
        "invested": invested,
        "cash": cash,
        "top_allocations": [{"stock": s, "amount": a} for s, a in top],
    }


def _sanitize_name(value: str) -> str:
    return "".join(ch if (ch.isalnum() or ch in ("-", "_")) else "_" for ch in value)


def _to_json_compatible_matrix(matrix):
    if matrix is None:
        return None
    if hasattr(matrix, "tolist"):
        return matrix.tolist()
    return matrix


def _extract_submatrix(matrix, indices: List[int]):
    if matrix is None or not indices:
        return None
    out = []
    for i in indices:
        row = []
        for j in indices:
            row.append(float(matrix[i][j]))
        out.append(row)
    return out


def _resolve_selected_qubo_matrix(qubo_details: dict):
    if not isinstance(qubo_details, dict):
        return None

    if "qubo_selected_submatrix" in qubo_details:
        return qubo_details.get("qubo_selected_submatrix")

    runs = qubo_details.get("runs")
    if isinstance(runs, list) and runs:
        first = runs[0]
        if isinstance(first, dict):
            return first.get("qubo_selected_submatrix")

    return None


def export_scenario_matrices(
    matrix_run_dir: Path,
    scenario_group: str,
    scenario_name: str,
    scenario_cfg: dict,
    selected_stocks: List[str],
    quantum_details: dict,
    matrix_cfg: dict,
):
    if matrix_run_dir is None:
        return None

    include_full_cov = bool(matrix_cfg.get("include_full_covariance", False))
    include_full_qubo = bool(matrix_cfg.get("include_full_qubo", False))
    include_selected_cov = bool(matrix_cfg.get("include_selected_covariance", True))
    include_selected_qubo = bool(matrix_cfg.get("include_selected_qubo", True))

    symbols_full = list(quantum_details.get("stock_symbols", []))
    selected_indices = [symbols_full.index(s) for s in selected_stocks if s in symbols_full]
    cov_full = quantum_details.get("covariance_full")
    qubo_details = quantum_details.get("qubo", {})

    qubo_full = None
    if isinstance(qubo_details, dict):
        qubo_full = qubo_details.get("qubo_matrix")

    payload = {
        "scenario_group": scenario_group,
        "scenario_name": scenario_name,
        "scenario": scenario_cfg,
        "symbols_full": symbols_full,
        "selected_stocks": selected_stocks,
        "selected_indices": selected_indices,
        "matrices": {},
    }

    if include_full_cov:
        payload["matrices"]["covariance_full"] = _to_json_compatible_matrix(cov_full)
    if include_selected_cov:
        payload["matrices"]["covariance_selected"] = _extract_submatrix(cov_full, selected_indices)
    if include_full_qubo:
        payload["matrices"]["qubo_full"] = _to_json_compatible_matrix(qubo_full)
    if include_selected_qubo:
        payload["matrices"]["qubo_selected"] = _resolve_selected_qubo_matrix(qubo_details)

    scenario_dir = matrix_run_dir / _sanitize_name(scenario_group)
    scenario_dir.mkdir(parents=True, exist_ok=True)
    out_file = scenario_dir / f"{_sanitize_name(scenario_name)}.json"

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    return str(out_file)


def evaluate_one(
    base_dir,
    name,
    cfg,
    prices_df,
    k_stocks,
    seed,
    min_train_coverage,
    min_test_points,
    eval_cfg,
    dynamic_k_cfg,
    qubo_cfg,
    weight_cfg,
    matrix_cfg=None,
    matrix_run_dir: Path | None = None,
    scenario_group: str = "scenario",
    rebalance_compare_enabled: bool = False,
    rebalance_frequency: str = "quarterly",
    baseline_method: str = "markowitz",
):
    crash_mod.validate_no_data_leakage(cfg["train_start"], cfg["train_end"], cfg["test_start"], cfg["test_end"])

    eligible = crash_mod.get_stock_universe(
        prices_df,
        cfg["train_start"], cfg["train_end"],
        cfg["test_start"], cfg["test_end"],
        min_coverage=min_train_coverage,
        min_test_points=min_test_points,
    )

    scenario_k = derive_scenario_k_from_train_window(
        base_dir,
        prices_df,
        cfg,
        eligible,
        {
            **eval_cfg,
            "dynamic_k": dynamic_k_cfg,
        },
        k_stocks,
    )

    if len(eligible) < scenario_k:
        return {
            "status": "skipped",
            "eligible_stocks": len(eligible),
            "reason": f"eligible<{scenario_k}",
            "scenario": cfg,
        }

    q_stocks = crash_mod.select_quantum_portfolio(
        prices_df,
        eligible,
        cfg["train_start"],
        cfg["train_end"],
        K=scenario_k,
        seed=seed,
        qubo_params=qubo_cfg,
        return_details=True,
        include_matrices=bool((matrix_cfg or {}).get("include_full_qubo", False)),
        verbose=False,
    )
    if isinstance(q_stocks, tuple):
        q_stocks, q_details = q_stocks
    else:
        q_details = {}
    q_w, _ = crash_mod.optimize_weights(
        q_stocks,
        prices_df,
        cfg["train_start"],
        cfg["train_end"],
        max_weight=float(weight_cfg.get("max_weight", 0.4)),
        min_weight=float(weight_cfg.get("min_weight", 0.0)),
        verbose=False,
    )
    q_bt = crash_mod.backtest_period(
        prices_df,
        q_stocks,
        q_w,
        cfg["test_start"],
        cfg["test_end"],
        verbose=False,
    )

    if rebalance_compare_enabled:
        q_rebal_bt = crash_mod.backtest_period_with_rebalance(
            prices_df,
            q_stocks,
            q_w,
            cfg["train_start"],
            cfg["test_start"],
            cfg["test_end"],
            rebalance_freq=rebalance_frequency,
            max_weight=float(weight_cfg.get("max_weight", 0.4)),
            min_weight=float(weight_cfg.get("min_weight", 0.0)),
            verbose=False,
        )

        baseline_method_norm = str(baseline_method).lower()
        if baseline_method_norm == "greedy":
            b_stocks = crash_mod.select_greedy_portfolio(
                prices_df,
                eligible,
                cfg["train_start"],
                cfg["train_end"],
                K=scenario_k,
                verbose=False,
            )
            baseline_name = "Greedy"
        else:
            b_stocks = crash_mod.select_classical_portfolio(
                prices_df,
                eligible,
                cfg["train_start"],
                cfg["train_end"],
                K=scenario_k,
                verbose=False,
            )
            baseline_name = "Markowitz"

        b_w, _ = crash_mod.optimize_weights(
            b_stocks,
            prices_df,
            cfg["train_start"],
            cfg["train_end"],
            max_weight=float(weight_cfg.get("max_weight", 0.4)),
            min_weight=float(weight_cfg.get("min_weight", 0.0)),
            verbose=False,
        )
        b_bt = crash_mod.backtest_period(
            prices_df,
            b_stocks,
            b_w,
            cfg["test_start"],
            cfg["test_end"],
            verbose=False,
        )
    else:
        g_stocks = crash_mod.select_greedy_portfolio(
            prices_df,
            eligible,
            cfg["train_start"],
            cfg["train_end"],
            K=scenario_k,
            verbose=False,
        )
        g_w, _ = crash_mod.optimize_weights(
            g_stocks,
            prices_df,
            cfg["train_start"],
            cfg["train_end"],
            max_weight=float(weight_cfg.get("max_weight", 0.4)),
            min_weight=float(weight_cfg.get("min_weight", 0.0)),
            verbose=False,
        )
        g_bt = crash_mod.backtest_period(
            prices_df,
            g_stocks,
            g_w,
            cfg["test_start"],
            cfg["test_end"],
            verbose=False,
        )

        c_stocks = crash_mod.select_classical_portfolio(
            prices_df,
            eligible,
            cfg["train_start"],
            cfg["train_end"],
            K=scenario_k,
            verbose=False,
        )
        c_w, _ = crash_mod.optimize_weights(
            c_stocks,
            prices_df,
            cfg["train_start"],
            cfg["train_end"],
            max_weight=float(weight_cfg.get("max_weight", 0.4)),
            min_weight=float(weight_cfg.get("min_weight", 0.0)),
            verbose=False,
        )
        c_bt = crash_mod.backtest_period(
            prices_df,
            c_stocks,
            c_w,
            cfg["test_start"],
            cfg["test_end"],
            verbose=False,
        )

    print(f"  Eligible stocks: {len(eligible)} | Scenario K: {scenario_k}")
    if rebalance_compare_enabled:
        print(
            "  Total return (%): "
            f"Quantum(NoRebal)={q_bt['total_return']:.2f}, "
            f"Quantum(Rebal-{rebalance_frequency})={q_rebal_bt['total_return']:.2f}, "
            f"{baseline_name}={b_bt['total_return']:.2f}"
        )
    else:
        print(
            "  Total return (%): "
            f"Quantum={q_bt['total_return']:.2f}, "
            f"Greedy={g_bt['total_return']:.2f}, "
            f"Classical={c_bt['total_return']:.2f}"
        )

    methods = {}
    budget = float(weight_cfg.get("budget", 0.0))
    if rebalance_compare_enabled:
        method_payload = {
            "Quantum_NoRebalance": q_bt,
            "Quantum_Rebalanced": q_rebal_bt,
            baseline_name: b_bt,
        }
    else:
        method_payload = {"Quantum": q_bt, "Greedy": g_bt, "Classical": c_bt}

    for method_name, metrics in method_payload.items():
        if metrics is None:
            continue
        if method_name in ("Quantum", "Quantum_NoRebalance", "Quantum_Rebalanced"):
            w_map = q_w
        elif method_name == "Greedy":
            w_map = g_w
        elif method_name == "Markowitz":
            w_map = b_w
        else:
            w_map = c_w

        methods[method_name] = {
            "total_return": float(metrics["total_return"]),
            "volatility": float(metrics["volatility"]),
            "max_drawdown": float(metrics["max_drawdown"]),
            "var_95": float(metrics["var_95"]),
            "sharpe": float(metrics["sharpe"]),
            "budget_partition": budget_partition_summary(w_map, budget),
        }

        if method_name == "Quantum_Rebalanced" and isinstance(metrics, dict):
            methods[method_name]["rebalance_frequency"] = metrics.get("rebalance_frequency")
            methods[method_name]["rebalances_applied"] = int(metrics.get("rebalances_applied", 0))

    matrix_export_file = None
    if bool((matrix_cfg or {}).get("enabled", False)) and q_details:
        matrix_export_file = export_scenario_matrices(
            matrix_run_dir=matrix_run_dir,
            scenario_group=scenario_group,
            scenario_name=name,
            scenario_cfg=cfg,
            selected_stocks=list(q_stocks),
            quantum_details=q_details,
            matrix_cfg=matrix_cfg,
        )

    return {
        "status": "ok",
        "scenario": cfg,
        "scenario_k": int(scenario_k),
        "eligible_stocks": len(eligible),
        "matrix_export_file": matrix_export_file,
        "methods": methods,
        "winners": {
            "best_total_return": winner_by_metric(methods, "total_return", maximize=True),
            "best_sharpe": winner_by_metric(methods, "sharpe", maximize=True),
            "best_max_drawdown": winner_by_metric(methods, "max_drawdown", maximize=True),
            "best_var_95": winner_by_metric(methods, "var_95", maximize=True),
        }
    }


def aggregate_winners(results: Dict[str, dict]):
    out = {
        "best_total_return": {},
        "best_sharpe": {},
        "best_max_drawdown": {},
        "best_var_95": {},
    }
    for _, sc in results.items():
        if sc.get("status") != "ok":
            continue
        for metric, winner in sc.get("winners", {}).items():
            if winner is None:
                continue
            out[metric][winner] = out[metric].get(winner, 0) + 1
    return out


def parse_args():
    parser = argparse.ArgumentParser(description="Unified train/test and crash comparison runner")
    parser.add_argument("--config", default="config/unified_compare_config.json", help="Path to unified config")
    parser.add_argument("--only", choices=["horizon", "crash", "all"], default="all")
    parser.add_argument("--k", type=int, default=None)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--universe-mode", choices=["full_universe", "nifty100_only"], default=None)
    parser.add_argument("--enable-rebalance-compare", action="store_true")
    parser.add_argument("--rebalance-frequency", choices=["monthly", "quarterly", "6M"], default="quarterly")
    parser.add_argument("--baseline-method", choices=["markowitz", "greedy"], default="markowitz")
    return parser.parse_args()


def write_rebalance_compare_artifacts(report: dict, out_dir: Path):
    """Write compact CSV/Markdown summaries for rebalance-compare runs."""
    rows = []
    for group_key, group_name in (("horizon_results", "horizon"), ("crash_results", "crash")):
        for scenario_name, scenario in report.get(group_key, {}).items():
            if scenario.get("status") != "ok":
                continue
            m = scenario.get("methods", {})
            q0 = m.get("Quantum_NoRebalance", {})
            qr = m.get("Quantum_Rebalanced", {})
            baseline_name = "Markowitz" if "Markowitz" in m else "Greedy"
            b = m.get(baseline_name, {})
            rows.append({
                "group": group_name,
                "scenario": scenario_name,
                "quantum_no_rebalance_total_return": q0.get("total_return"),
                "quantum_rebalanced_total_return": qr.get("total_return"),
                f"{baseline_name.lower()}_total_return": b.get("total_return"),
                "winner_total_return": scenario.get("winners", {}).get("best_total_return"),
                "winner_sharpe": scenario.get("winners", {}).get("best_sharpe"),
                "rebalances_applied": qr.get("rebalances_applied", 0),
            })

    csv_path = out_dir / "rebalance_compare_summary.csv"
    pd.DataFrame(rows).to_csv(csv_path, index=False)

    md_lines = [
        "# Rebalance Comparison Summary",
        "",
        "Methods compared per scenario:",
        "1. Quantum_NoRebalance",
        "2. Quantum_Rebalanced",
        "3. Markowitz (or Greedy if selected)",
        "",
        "| Group | Scenario | Quantum NoRebal | Quantum Rebal | Baseline | Winner Return | Winner Sharpe | Rebalances |",
        "|---|---|---:|---:|---:|---|---|---:|",
    ]

    for r in rows:
        baseline_value = r.get("markowitz_total_return", r.get("greedy_total_return"))
        md_lines.append(
            f"| {r['group']} | {r['scenario']} | {r['quantum_no_rebalance_total_return']:.2f} "
            f"| {r['quantum_rebalanced_total_return']:.2f} | {baseline_value:.2f} "
            f"| {r['winner_total_return']} | {r['winner_sharpe']} | {r['rebalances_applied']} |"
        )

    md_path = out_dir / "rebalance_compare_summary.md"
    md_path.write_text("\n".join(md_lines), encoding="utf-8")


def main():
    args = parse_args()
    base_dir = Path(__file__).parent
    config = load_json(base_dir / args.config)

    dataset = choose_best_dataset(base_dir, config["dataset_candidates"])
    print("\n[DATASET VERIFICATION]")
    print(f"Selected dataset: {dataset['path']}")
    print(f"Rows={dataset['rows']}, Assets={dataset['assets']}, DateRange={dataset['start']} -> {dataset['end']}")

    prices_df_raw = pd.read_csv(dataset["path"], parse_dates=["Date"]).sort_values("Date")

    universe_cfg = config.get("universe_filter", {})
    default_universe_mode = universe_cfg.get("mode", "full_universe")
    if args.universe_mode:
        universe_mode_horizon = args.universe_mode
        universe_mode_crash = args.universe_mode
    else:
        universe_mode_horizon = universe_cfg.get("mode_horizon", default_universe_mode)
        universe_mode_crash = universe_cfg.get("mode_crash", default_universe_mode)
    nifty100_sectors_path = universe_cfg.get("nifty100_sectors_path", "config/nifty100_sectors.json")

    allowed_symbols = None
    if universe_mode_horizon == "nifty100_only" or universe_mode_crash == "nifty100_only":
        allowed_symbols = load_nifty100_symbols(base_dir, nifty100_sectors_path)

    prices_df_horizon, universe_stats_horizon = apply_universe_filter(
        prices_df_raw,
        universe_mode_horizon,
        allowed_symbols,
    )
    prices_df_crash, universe_stats_crash = apply_universe_filter(
        prices_df_raw,
        universe_mode_crash,
        allowed_symbols,
    )

    print("\n[UNIVERSE FILTER]")
    print(f"Horizon mode: {universe_mode_horizon}")
    print(
        "Horizon assets after filter: "
        f"{universe_stats_horizon['filtered_assets']} "
        f"(dropped {universe_stats_horizon['dropped_assets']} from {universe_stats_horizon['raw_assets']})"
    )
    print(f"Crash mode: {universe_mode_crash}")
    print(
        "Crash assets after filter: "
        f"{universe_stats_crash['filtered_assets']} "
        f"(dropped {universe_stats_crash['dropped_assets']} from {universe_stats_crash['raw_assets']})"
    )

    eval_cfg = config["evaluation"]
    k_stocks = resolve_k_stocks(base_dir, eval_cfg, args.k)
    seed = int(args.seed if args.seed is not None else eval_cfg["seed"])
    min_train_coverage = float(eval_cfg["min_train_coverage"])
    min_test_points = int(eval_cfg["min_test_points"])
    qubo_cfg = config.get("qubo", {})
    weight_cfg = config.get("weight_optimization", {})
    dynamic_k_cfg = config.get("dynamic_k", {"enabled": False})
    matrix_cfg = config.get("matrix_exports", {})
    rebalance_compare_enabled = bool(args.enable_rebalance_compare)
    rebalance_frequency = str(args.rebalance_frequency)
    baseline_method = str(args.baseline_method)

    matrix_run_dir = None
    if bool(matrix_cfg.get("enabled", False)):
        matrix_root = (base_dir / matrix_cfg.get("output_root", "run_artifacts/matrix_exports")).resolve()
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        matrix_run_dir = matrix_root / run_id
        matrix_run_dir.mkdir(parents=True, exist_ok=True)

    report = {
        "dataset": {
            "path": dataset["path"],
            "rows": dataset["rows"],
            "assets": dataset["assets"],
            "assets_after_universe_filter_horizon": int(universe_stats_horizon["filtered_assets"]),
            "assets_after_universe_filter_crash": int(universe_stats_crash["filtered_assets"]),
            "start_date": dataset["start"],
            "end_date": dataset["end"],
        },
        "methodology_phases": [
            "phase_01_data_preparation",
            "phase_02_cardinality_determination",
            "phase_03_qubo_formulation",
            "phase_04_quantum_selection",
            "phase_05_rebalancing",
            "phase_06_weight_optimization",
            "phase_07_strategy_comparison",
            "phase_08_crash_and_regime_evaluation"
        ],
        "parameters": {
            "k_stocks": k_stocks,
            "k_mode": eval_cfg.get("k_mode", "fixed"),
            "seed": seed,
            "min_train_coverage": min_train_coverage,
            "min_test_points": min_test_points,
            "universe_mode_horizon": universe_mode_horizon,
            "universe_mode_crash": universe_mode_crash,
            "nifty100_sectors_path": nifty100_sectors_path,
            "qubo": qubo_cfg,
            "weight_optimization": weight_cfg,
        },
        "horizon_results": {},
        "crash_results": {},
        "winner_counts": {},
        "rebalance_compare": {
            "enabled": rebalance_compare_enabled,
            "frequency": rebalance_frequency if rebalance_compare_enabled else None,
            "baseline_method": baseline_method if rebalance_compare_enabled else None,
        },
        "matrix_exports": {
            "enabled": bool(matrix_cfg.get("enabled", False)),
            "run_dir": str(matrix_run_dir) if matrix_run_dir else None,
        },
    }

    if args.only in ("horizon", "all"):
        train_window_mode = str(eval_cfg.get("train_window_mode", "rolling"))
        scenarios = build_horizon_scenarios(
            dataset["end_ts"],
            eval_cfg["horizon_months"],
            eval_cfg["train_months_by_horizon"],
            train_window_mode=train_window_mode,
            dataset_start_ts=dataset["start"],
        )
        for name, cfg in scenarios.items():
            print(f"\n[HORIZON] {name}")
            report["horizon_results"][name] = evaluate_one(
                base_dir,
                name,
                cfg,
                prices_df_horizon,
                k_stocks,
                seed,
                min_train_coverage,
                min_test_points,
                eval_cfg,
                dynamic_k_cfg,
                qubo_cfg,
                weight_cfg,
                matrix_cfg,
                matrix_run_dir,
                "horizon",
                rebalance_compare_enabled,
                rebalance_frequency,
                baseline_method,
            )
        report["winner_counts"]["horizon"] = aggregate_winners(report["horizon_results"])

    if args.only in ("crash", "all"):
        for name, cfg in config["crash_scenarios"].items():
            print(f"\n[CRASH] {name}")
            report["crash_results"][name] = evaluate_one(
                base_dir,
                name,
                cfg,
                prices_df_crash,
                k_stocks,
                seed,
                min_train_coverage,
                min_test_points,
                eval_cfg,
                dynamic_k_cfg,
                qubo_cfg,
                weight_cfg,
                matrix_cfg,
                matrix_run_dir,
                "crash",
                rebalance_compare_enabled,
                rebalance_frequency,
                baseline_method,
            )
        report["winner_counts"]["crash"] = aggregate_winners(report["crash_results"])

    out_dir = base_dir / "results"
    out_dir.mkdir(exist_ok=True)
    out_file = out_dir / "unified_train_test_compare.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    if rebalance_compare_enabled:
        write_rebalance_compare_artifacts(report, out_dir)

    print("\n[OUTPUT]")
    print(f"Saved report: {out_file}")
    if matrix_run_dir is not None:
        print(f"Saved matrix artifacts: {matrix_run_dir}")


if __name__ == "__main__":
    main()
