#!/usr/bin/env python3
"""
Generate presentation-ready method comparison graphs from unified results.

Outputs:
1) Classical vs Quantum (clear two-line scenario chart)
2) Classical vs Quantum vs Quantum+Rebal (clear three-line scenario chart)
3) Sharpe companion charts for both views
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import phase_08_crash_and_regime_evaluation as crash_mod
import unified_train_test_compare as utc


def _load_report(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _scenario_sort_key(row: dict) -> tuple[int, int, str]:
    group = row["group"]
    scenario = row["scenario"]

    if group == "horizon":
        m = re.search(r"Horizon_(\d+)M", scenario)
        horizon_months = int(m.group(1)) if m else 999
        return (0, horizon_months, scenario)

    crash_order = {
        "COVID Peak Crash": 0,
        "China Bubble Burst Peak": 1,
        "European Debt Stress": 2,
        "2022 Global Bear Phase": 3,
    }
    return (1, crash_order.get(scenario, 999), scenario)


def _short_label(group: str, scenario: str) -> str:
    if group == "horizon":
        m = re.search(r"Horizon_(\d+)M", scenario)
        h = m.group(1) if m else "?"
        return f"H-{h}M"

    mapping = {
        "COVID Peak Crash": "C-COVID",
        "China Bubble Burst Peak": "C-CHINA",
        "European Debt Stress": "C-EU",
        "2022 Global Bear Phase": "C-2022",
    }
    return mapping.get(scenario, f"C-{scenario[:10].upper()}")


def _collect_rows(report: dict) -> pd.DataFrame:
    rows = []

    def collect(group_key: str, group_name: str) -> None:
        for scenario_name, scenario in report.get(group_key, {}).items():
            if scenario.get("status") != "ok":
                continue

            methods = scenario.get("methods", {})

            # Support both standard mode and rebalance-compare mode.
            q = methods.get("Quantum_NoRebalance", methods.get("Quantum"))
            c = methods.get("Markowitz", methods.get("Classical"))
            qr = methods.get("Quantum_Rebalanced")

            if q is None or c is None:
                continue

            rows.append(
                {
                    "group": group_name,
                    "scenario": scenario_name,
                    "label": _short_label(group_name, scenario_name),
                    "classical_return": float(c.get("total_return", np.nan)),
                    "classical_sharpe": float(c.get("sharpe", np.nan)),
                    "quantum_return": float(q.get("total_return", np.nan)),
                    "quantum_sharpe": float(q.get("sharpe", np.nan)),
                    "quantum_rebal_return": float(qr.get("total_return", np.nan)) if qr else np.nan,
                    "quantum_rebal_sharpe": float(qr.get("sharpe", np.nan)) if qr else np.nan,
                }
            )

    collect("horizon_results", "horizon")
    collect("crash_results", "crash")

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    ordered = sorted(df.to_dict(orient="records"), key=_scenario_sort_key)
    return pd.DataFrame(ordered)


def _style_axis(ax, title: str, ylabel: str) -> None:
    ax.set_title(title, fontsize=13, fontweight="bold", pad=10)
    ax.set_ylabel(ylabel, fontsize=11)
    ax.grid(True, alpha=0.25, linestyle="--", linewidth=0.8)
    ax.axhline(0, color="#444", linewidth=0.9)


def _annotate_points(ax, x: np.ndarray, y: np.ndarray, color: str) -> None:
    for xi, yi in zip(x, y):
        if np.isnan(yi):
            continue
        offset = 8 if yi >= 0 else -12
        va = "bottom" if yi >= 0 else "top"
        ax.annotate(
            f"{yi:.1f}",
            (xi, yi),
            textcoords="offset points",
            xytext=(0, offset),
            ha="center",
            va=va,
            color=color,
            fontsize=8,
        )


def _plot_return_lines(df: pd.DataFrame, out_two: Path, out_three: Path) -> None:
    x = np.arange(len(df))
    labels = df["label"].tolist()

    # Figure 1: Classical vs Quantum (clean, like paper-style comparison).
    fig1, ax1 = plt.subplots(figsize=(14, 6.8))
    c_ret = df["classical_return"].values
    q_ret = df["quantum_return"].values

    ax1.plot(x, c_ret, marker="o", linewidth=2.2, markersize=5, color="#d62728", label="Classical")
    ax1.plot(x, q_ret, marker="o", linewidth=2.2, markersize=5, color="#1f77b4", label="Quantum")
    _style_axis(ax1, "Scenario-wise Return Comparison: Classical vs Quantum", "Total Return (%)")
    _annotate_points(ax1, x, c_ret, "#d62728")
    _annotate_points(ax1, x, q_ret, "#1f77b4")

    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, rotation=28, ha="right")
    ax1.set_xlabel("Scenarios (H = Horizon, C = Crash)", fontsize=10)
    ax1.legend(loc="upper left", frameon=True, facecolor="white", edgecolor="#cccccc")

    fig1.tight_layout()
    fig1.savefig(out_two, dpi=220, bbox_inches="tight")
    plt.close(fig1)

    # Figure 2: Classical vs Quantum vs Quantum+Rebal.
    has_rebal = df["quantum_rebal_return"].notna().any()
    if not has_rebal:
        return

    fig2, ax2 = plt.subplots(figsize=(14, 6.8))
    qr_ret = df["quantum_rebal_return"].values

    ax2.plot(x, c_ret, marker="o", linewidth=2.0, markersize=5, color="#d62728", label="Classical")
    ax2.plot(x, q_ret, marker="o", linewidth=2.0, markersize=5, color="#1f77b4", label="Quantum")
    ax2.plot(x, qr_ret, marker="o", linewidth=2.4, markersize=5, color="#2ca02c", label="Quantum + Rebalancing")
    _style_axis(
        ax2,
        "Scenario-wise Return Comparison: Classical vs Quantum vs Quantum+Rebal",
        "Total Return (%)",
    )
    _annotate_points(ax2, x, c_ret, "#d62728")
    _annotate_points(ax2, x, q_ret, "#1f77b4")
    _annotate_points(ax2, x, qr_ret, "#2ca02c")

    ax2.set_xticks(x)
    ax2.set_xticklabels(labels, rotation=28, ha="right")
    ax2.set_xlabel("Scenarios (H = Horizon, C = Crash)", fontsize=10)
    ax2.legend(loc="upper left", frameon=True, facecolor="white", edgecolor="#cccccc")

    fig2.tight_layout()
    fig2.savefig(out_three, dpi=220, bbox_inches="tight")
    plt.close(fig2)


def _plot_sharpe_lines(df: pd.DataFrame, out_two: Path, out_three: Path) -> None:
    x = np.arange(len(df))
    labels = df["label"].tolist()

    c_sh = df["classical_sharpe"].values
    q_sh = df["quantum_sharpe"].values

    fig1, ax1 = plt.subplots(figsize=(14, 6.8))
    ax1.plot(x, c_sh, marker="o", linewidth=2.2, markersize=5, color="#d62728", label="Classical")
    ax1.plot(x, q_sh, marker="o", linewidth=2.2, markersize=5, color="#1f77b4", label="Quantum")
    _style_axis(ax1, "Scenario-wise Sharpe Comparison: Classical vs Quantum", "Sharpe")
    _annotate_points(ax1, x, c_sh, "#d62728")
    _annotate_points(ax1, x, q_sh, "#1f77b4")

    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, rotation=28, ha="right")
    ax1.set_xlabel("Scenarios (H = Horizon, C = Crash)", fontsize=10)
    ax1.legend(loc="upper left", frameon=True, facecolor="white", edgecolor="#cccccc")

    fig1.tight_layout()
    fig1.savefig(out_two, dpi=220, bbox_inches="tight")
    plt.close(fig1)

    has_rebal = df["quantum_rebal_sharpe"].notna().any()
    if not has_rebal:
        return

    qr_sh = df["quantum_rebal_sharpe"].values

    fig2, ax2 = plt.subplots(figsize=(14, 6.8))
    ax2.plot(x, c_sh, marker="o", linewidth=2.0, markersize=5, color="#d62728", label="Classical")
    ax2.plot(x, q_sh, marker="o", linewidth=2.0, markersize=5, color="#1f77b4", label="Quantum")
    ax2.plot(x, qr_sh, marker="o", linewidth=2.4, markersize=5, color="#2ca02c", label="Quantum + Rebalancing")
    _style_axis(
        ax2,
        "Scenario-wise Sharpe Comparison: Classical vs Quantum vs Quantum+Rebal",
        "Sharpe",
    )
    _annotate_points(ax2, x, c_sh, "#d62728")
    _annotate_points(ax2, x, q_sh, "#1f77b4")
    _annotate_points(ax2, x, qr_sh, "#2ca02c")

    ax2.set_xticks(x)
    ax2.set_xticklabels(labels, rotation=28, ha="right")
    ax2.set_xlabel("Scenarios (H = Horizon, C = Crash)", fontsize=10)
    ax2.legend(loc="upper left", frameon=True, facecolor="white", edgecolor="#cccccc")

    fig2.tight_layout()
    fig2.savefig(out_three, dpi=220, bbox_inches="tight")
    plt.close(fig2)


def _series_from_backtest(
    bt: dict,
    initial_capital: float = 1_000_000.0,
    fallback_dates: pd.Series | None = None,
) -> pd.Series:
    if bt is None:
        return pd.Series(dtype=float)
    raw_dates = bt.get("dates", [])
    dates = pd.to_datetime(raw_dates, errors="coerce")
    cum = np.array(bt.get("cumulative_returns", []), dtype=float)
    if len(cum) == 0:
        return pd.Series(dtype=float)

    use_fallback = False
    if len(dates) == 0 or dates.isna().all():
        use_fallback = True
    else:
        # Backtest currently may return positional integer indices; those parse near epoch.
        if dates.max().year < 1990:
            use_fallback = True

    if use_fallback:
        if fallback_dates is None or fallback_dates.empty:
            return pd.Series(dtype=float)
        n = min(len(cum), len(fallback_dates))
        dates = pd.to_datetime(fallback_dates.iloc[:n]).values
        cum = cum[:n]

    values = initial_capital * cum
    return pd.Series(values, index=dates).sort_index()


def _build_runtime_context(base: Path) -> dict:
    config = utc.load_json(base / "config" / "unified_compare_config.json")
    dataset = utc.choose_best_dataset(base, config["dataset_candidates"])
    prices_df_raw = pd.read_csv(dataset["path"], parse_dates=["Date"]).sort_values("Date")

    universe_cfg = config.get("universe_filter", {})
    universe_mode = universe_cfg.get("mode", "full_universe")
    nifty100_sectors_path = universe_cfg.get("nifty100_sectors_path", "config/nifty100_sectors.json")

    allowed_symbols = None
    if universe_mode == "nifty100_only":
        allowed_symbols = utc.load_nifty100_symbols(base, nifty100_sectors_path)

    prices_df, _ = utc.apply_universe_filter(prices_df_raw, universe_mode, allowed_symbols)

    eval_cfg = config["evaluation"]
    dynamic_k_cfg = config.get("dynamic_k", {"enabled": False})
    qubo_cfg = config.get("qubo", {})
    weight_cfg = config.get("weight_optimization", {})

    # Keep scenario chart generation responsive.
    qubo_cfg_fast = dict(qubo_cfg)
    qubo_cfg_fast["ensemble_enabled"] = False
    qubo_cfg_fast["max_iter"] = min(int(qubo_cfg_fast.get("max_iter", 2000)), 600)

    return {
        "config": config,
        "dataset": dataset,
        "prices_df": prices_df,
        "eval_cfg": eval_cfg,
        "dynamic_k_cfg": dynamic_k_cfg,
        "qubo_cfg_fast": qubo_cfg_fast,
        "weight_cfg": weight_cfg,
    }


def _monthly_return_for_scenario(
    base: Path,
    out_dir: Path,
    runtime: dict,
    scenario_name: str,
    scenario_cfg: dict,
    output_slug: str,
) -> tuple[Path, Path]:
    dataset = runtime["dataset"]
    prices_df = runtime["prices_df"]
    eval_cfg = runtime["eval_cfg"]
    dynamic_k_cfg = runtime["dynamic_k_cfg"]
    qubo_cfg_fast = runtime["qubo_cfg_fast"]
    weight_cfg = runtime["weight_cfg"]

    k_stocks = utc.resolve_k_stocks(base, eval_cfg, cli_k=None)
    seed = int(eval_cfg.get("seed", 42))
    min_train_coverage = float(eval_cfg.get("min_train_coverage", 0.8))
    min_test_points = int(eval_cfg.get("min_test_points", 20))

    cfg = scenario_cfg
    crash_mod.validate_no_data_leakage(cfg["train_start"], cfg["train_end"], cfg["test_start"], cfg["test_end"])

    eligible = crash_mod.get_stock_universe(
        prices_df,
        cfg["train_start"],
        cfg["train_end"],
        cfg["test_start"],
        cfg["test_end"],
        min_coverage=min_train_coverage,
        min_test_points=min_test_points,
    )

    scenario_k = utc.derive_scenario_k_from_train_window(
        base,
        prices_df,
        cfg,
        eligible,
        {**eval_cfg, "dynamic_k": dynamic_k_cfg},
        k_stocks,
    )

    # Quantum (no rebalance)
    q_sel = crash_mod.select_quantum_portfolio(
        prices_df,
        eligible,
        cfg["train_start"],
        cfg["train_end"],
        K=scenario_k,
        seed=seed,
        qubo_params=qubo_cfg_fast,
        return_details=False,
        verbose=False,
    )
    q_w, _ = crash_mod.optimize_weights(
        q_sel,
        prices_df,
        cfg["train_start"],
        cfg["train_end"],
        max_weight=float(weight_cfg.get("max_weight", 0.4)),
        min_weight=float(weight_cfg.get("min_weight", 0.0)),
        verbose=False,
    )
    q_bt = crash_mod.backtest_period(
        prices_df,
        q_sel,
        q_w,
        cfg["test_start"],
        cfg["test_end"],
        verbose=False,
    )

    # Quantum (rebalanced)
    q_rebal_bt = crash_mod.backtest_period_with_rebalance(
        prices_df,
        q_sel,
        q_w,
        cfg["train_start"],
        cfg["test_start"],
        cfg["test_end"],
        rebalance_freq="quarterly",
        max_weight=float(weight_cfg.get("max_weight", 0.4)),
        min_weight=float(weight_cfg.get("min_weight", 0.0)),
        verbose=False,
    )

    # Classical (Markowitz)
    c_sel = crash_mod.select_classical_portfolio(
        prices_df,
        eligible,
        cfg["train_start"],
        cfg["train_end"],
        K=scenario_k,
        verbose=False,
    )
    c_w, _ = crash_mod.optimize_weights(
        c_sel,
        prices_df,
        cfg["train_start"],
        cfg["train_end"],
        max_weight=float(weight_cfg.get("max_weight", 0.4)),
        min_weight=float(weight_cfg.get("min_weight", 0.0)),
        verbose=False,
    )
    c_bt = crash_mod.backtest_period(
        prices_df,
        c_sel,
        c_w,
        cfg["test_start"],
        cfg["test_end"],
        verbose=False,
    )

    test_mask = (prices_df["Date"] >= cfg["test_start"]) & (prices_df["Date"] <= cfg["test_end"])
    # pct_change().dropna() in backtest starts from second row of test period
    fallback_dates = pd.to_datetime(prices_df.loc[test_mask, "Date"]).reset_index(drop=True).iloc[1:]

    q_series = _series_from_backtest(q_bt, fallback_dates=fallback_dates)
    q_rebal_series = _series_from_backtest(q_rebal_bt, fallback_dates=fallback_dates)
    c_series = _series_from_backtest(c_bt, fallback_dates=fallback_dates)

    monthly = pd.concat(
        [
            c_series.resample("ME").last().rename("Classical"),
            q_series.resample("ME").last().rename("Quantum"),
            q_rebal_series.resample("ME").last().rename("Quantum+Rebal"),
        ],
        axis=1,
    ).dropna(how="all")

    # Convert to cumulative return (%) from first monthly point for each method.
    monthly_ret = monthly.apply(lambda s: (s / s.dropna().iloc[0] - 1.0) * 100.0 if s.dropna().size else s)

    csv_out = out_dir / f"{output_slug}_monthly_return_movement.csv"
    monthly_ret.to_csv(csv_out, index_label="Month")

    fig, ax = plt.subplots(figsize=(13, 6.8))
    x = monthly_ret.index
    ax.plot(x, monthly_ret["Classical"], marker="o", linewidth=2.1, color="#d62728", label="Classical")
    ax.plot(x, monthly_ret["Quantum"], marker="o", linewidth=2.1, color="#1f77b4", label="Quantum")
    ax.plot(x, monthly_ret["Quantum+Rebal"], marker="o", linewidth=2.4, color="#2ca02c", label="Quantum + Rebalancing")

    ax.set_title(f"Monthly Cumulative Return (%) - {scenario_name}", fontsize=13, fontweight="bold", pad=10)
    ax.set_ylabel("Cumulative Return (%)", fontsize=11)
    ax.set_xlabel("Month", fontsize=10)
    ax.axhline(0, color="#555", linewidth=0.9)
    ax.grid(True, alpha=0.25, linestyle="--", linewidth=0.8)
    ax.legend(loc="upper left", frameon=True, facecolor="white", edgecolor="#cccccc")

    for label in ax.get_xticklabels():
        label.set_rotation(30)
        label.set_ha("right")

    png_out = out_dir / f"graph_{output_slug}_monthly_return_movement.png"
    fig.tight_layout()
    fig.savefig(png_out, dpi=220, bbox_inches="tight")
    plt.close(fig)

    return png_out, csv_out


def main() -> int:
    base = Path(__file__).resolve().parent
    report_path = base / "results" / "unified_train_test_compare.json"
    out_dir = base / "results"
    out_dir.mkdir(parents=True, exist_ok=True)

    report = _load_report(report_path)
    df = _collect_rows(report)

    if df.empty:
        raise RuntimeError("No comparable scenarios found in unified report")

    csv_path = out_dir / "method_comparison_all_scenarios.csv"
    df.to_csv(csv_path, index=False)

    # Returns charts
    ret_two = out_dir / "graph_classical_vs_quantum.png"
    ret_three = out_dir / "graph_classical_quantum_quantum_rebal.png"
    _plot_return_lines(df, ret_two, ret_three)

    # Sharpe charts
    sh_two = out_dir / "graph_classical_vs_quantum_sharpe.png"
    sh_three = out_dir / "graph_classical_quantum_quantum_rebal_sharpe.png"
    _plot_sharpe_lines(df, sh_two, sh_three)

    print("[OUTPUT]")
    print(f"Table: {csv_path}")
    print(f"Returns Graph 1: {ret_two}")
    if ret_three.exists():
        print(f"Returns Graph 2: {ret_three}")
    else:
        print("Returns Graph 2: Skipped (no rebalanced results in report)")

    print(f"Sharpe Graph 1: {sh_two}")
    if sh_three.exists():
        print(f"Sharpe Graph 2: {sh_three}")
    else:
        print("Sharpe Graph 2: Skipped (no rebalanced results in report)")

    runtime = _build_runtime_context(base)
    cfg = runtime["config"]
    eval_cfg = runtime["eval_cfg"]
    dataset = runtime["dataset"]

    horizon_scenarios = utc.build_horizon_scenarios(
        dataset["end_ts"],
        eval_cfg["horizon_months"],
        eval_cfg["train_months_by_horizon"],
        train_window_mode=str(eval_cfg.get("train_window_mode", "rolling")),
        dataset_start_ts=dataset["start"],
    )

    required_horizons = ["Horizon_6M_Train_60M", "Horizon_12M_Train_60M", "Horizon_24M_Train_60M"]
    for scenario_name in required_horizons:
        if scenario_name not in horizon_scenarios:
            continue
        slug = scenario_name.lower().replace("_train_60m", "").replace("horizon_", "horizon_")
        png_out, csv_out = _monthly_return_for_scenario(
            base,
            out_dir,
            runtime,
            scenario_name=scenario_name,
            scenario_cfg=horizon_scenarios[scenario_name],
            output_slug=slug,
        )
        print(f"Monthly Return Graph ({scenario_name}): {png_out}")
        print(f"Monthly Return Table ({scenario_name}): {csv_out}")

    for crash_name, crash_cfg in cfg.get("crash_scenarios", {}).items():
        crash_slug = "crash_" + re.sub(r"[^a-z0-9]+", "_", crash_name.lower()).strip("_")
        png_out, csv_out = _monthly_return_for_scenario(
            base,
            out_dir,
            runtime,
            scenario_name=crash_name,
            scenario_cfg=crash_cfg,
            output_slug=crash_slug,
        )
        print(f"Monthly Return Graph ({crash_name}): {png_out}")
        print(f"Monthly Return Table ({crash_name}): {csv_out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
