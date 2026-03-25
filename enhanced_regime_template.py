"""
Enhanced Quantum Portfolio Evaluation

Adds:
1. Fully reproducible runs via fixed random seeds.
2. Regime scenario testing (bear/crash, bull, present).
3. Rolling walk-forward evaluation from 2020 to latest date.
4. Final winner-count report by regime.

Notes:
- Crash scenarios use 6-12 month training windows before crash tests.
- Stock universe is filtered primarily on train-period data sufficiency.
"""

from __future__ import annotations

import argparse
import json
from copy import deepcopy
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

from phase_08_crash_and_regime_evaluation import (
    load_complete_data,
    validate_no_data_leakage,
    select_quantum_portfolio,
    select_greedy_portfolio,
    select_classical_portfolio,
    optimize_weights,
    backtest_period,
)


BASE_SEED = 42
K_STOCKS = 10
MIN_TRAIN_COVERAGE = 0.80
MIN_TEST_POINTS = 20

WF_START_TEST = "2020-01-01"
WF_TRAIN_MONTHS = 12
WF_TEST_MONTHS = 6
WF_STEP_MONTHS = 12
WF_MIN_REMAINING_DAYS = 30

ARTIFACTS_ENABLED = True
ARTIFACTS_OUTPUT_DIR = Path("results/enhanced_artifacts")
INCLUDE_FULL_QUBO_MATRIX = False

SECTOR_CONSTRAINTS_ENABLED = True
MAX_SECTOR_WEIGHT = 0.45
SECTOR_METADATA_PATH = Path("../dataset/stock_metadata.csv")
SECTOR_SYMBOL_COLUMN = "Symbol"
SECTOR_COLUMN = "Industry"

DEFAULT_CONFIG_PATH = Path("config/enhanced_evaluation_config.json")


DEFAULT_REGIME_SCENARIOS = {
    "Bear Market - Crashes": {
        "COVID Peak Crash": {
            "train_start": "2019-02-20",
            "train_end": "2020-02-19",
            "test_start": "2020-02-20",
            "test_end": "2020-04-30",
            "description": "12M train before COVID crash peak, test during crash peak",
            "regime": "Crash",
        },
        "China Bubble Burst Peak": {
            "train_start": "2014-06-12",
            "train_end": "2015-06-11",
            "test_start": "2015-06-12",
            "test_end": "2015-09-30",
            "description": "12M train before China crash, test peak drawdown months",
            "regime": "Crash",
        },
        "European Debt Stress": {
            "train_start": "2011-03-14",
            "train_end": "2012-03-13",
            "test_start": "2012-03-14",
            "test_end": "2012-09-30",
            "description": "~12M train before Euro stress, test during stress window",
            "regime": "Crash",
        },
        "2022 Global Bear Phase": {
            "train_start": "2021-01-01",
            "train_end": "2021-12-31",
            "test_start": "2022-01-01",
            "test_end": "2022-06-30",
            "description": "12M train before 2022 bear phase, test in first drawdown half",
            "regime": "Crash",
        },
    },
    "Bull Market - Recovery/Profit": {
        "Post-COVID Recovery": {
            "train_start": "2019-04-01",
            "train_end": "2020-03-31",
            "test_start": "2020-04-01",
            "test_end": "2021-03-31",
            "description": "Train pre-recovery, test in strong recovery year",
            "regime": "Normal",
        },
        "2023 Bull Run": {
            "train_start": "2022-01-01",
            "train_end": "2022-12-31",
            "test_start": "2023-01-01",
            "test_end": "2023-12-31",
            "description": "Train in 2022, test full 2023 bull year",
            "regime": "Normal",
        },
        "2024 Momentum Year": {
            "train_start": "2023-01-01",
            "train_end": "2023-12-31",
            "test_start": "2024-01-01",
            "test_end": "2024-12-31",
            "description": "Train in 2023, test full 2024 momentum year",
            "regime": "Normal",
        },
    },
    "Present": {
        "Present to Mar-11-2026": {
            "train_start": "2024-03-11",
            "train_end": "2025-03-10",
            "test_start": "2025-03-11",
            "test_end": "2026-03-11",
            "description": "Train 1Y before present period, test until latest available date",
            "regime": "Present",
        }
    },
}

REGIME_SCENARIOS = deepcopy(DEFAULT_REGIME_SCENARIOS)


def load_runtime_config(config_path: Path) -> dict:
    """Load optional runtime config from JSON file."""
    if not config_path.exists():
        return {}

    with open(config_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError("Config file must contain a JSON object")

    return data


def apply_runtime_config(config_data: dict) -> None:
    """Apply config values to runtime globals."""
    global BASE_SEED, K_STOCKS, MIN_TRAIN_COVERAGE, MIN_TEST_POINTS
    global WF_START_TEST, WF_TRAIN_MONTHS, WF_TEST_MONTHS, WF_STEP_MONTHS, WF_MIN_REMAINING_DAYS
    global ARTIFACTS_ENABLED, ARTIFACTS_OUTPUT_DIR, INCLUDE_FULL_QUBO_MATRIX
    global SECTOR_CONSTRAINTS_ENABLED, MAX_SECTOR_WEIGHT
    global SECTOR_METADATA_PATH, SECTOR_SYMBOL_COLUMN, SECTOR_COLUMN
    global REGIME_SCENARIOS

    BASE_SEED = int(config_data.get("base_seed", BASE_SEED))
    K_STOCKS = int(config_data.get("k_stocks", K_STOCKS))
    MIN_TRAIN_COVERAGE = float(config_data.get("min_train_coverage", MIN_TRAIN_COVERAGE))
    MIN_TEST_POINTS = int(config_data.get("min_test_points", MIN_TEST_POINTS))

    walkforward = config_data.get("walkforward", {})
    if isinstance(walkforward, dict):
        WF_START_TEST = str(walkforward.get("start_test", WF_START_TEST))
        WF_TRAIN_MONTHS = int(walkforward.get("train_months", WF_TRAIN_MONTHS))
        WF_TEST_MONTHS = int(walkforward.get("test_months", WF_TEST_MONTHS))
        WF_STEP_MONTHS = int(walkforward.get("step_months", WF_STEP_MONTHS))
        WF_MIN_REMAINING_DAYS = int(walkforward.get("min_remaining_days", WF_MIN_REMAINING_DAYS))

    scenarios = config_data.get("regime_scenarios")
    if isinstance(scenarios, dict) and scenarios:
        REGIME_SCENARIOS = scenarios

    artifacts = config_data.get("artifacts", {})
    if isinstance(artifacts, dict):
        ARTIFACTS_ENABLED = bool(artifacts.get("enabled", ARTIFACTS_ENABLED))
        ARTIFACTS_OUTPUT_DIR = Path(str(artifacts.get("output_dir", ARTIFACTS_OUTPUT_DIR)))
        INCLUDE_FULL_QUBO_MATRIX = bool(
            artifacts.get("include_full_qubo_matrix", INCLUDE_FULL_QUBO_MATRIX)
        )

    sector_cfg = config_data.get("sector_constraints", {})
    if isinstance(sector_cfg, dict):
        SECTOR_CONSTRAINTS_ENABLED = bool(
            sector_cfg.get("enabled", SECTOR_CONSTRAINTS_ENABLED)
        )
        MAX_SECTOR_WEIGHT = float(sector_cfg.get("max_sector_weight", MAX_SECTOR_WEIGHT))
        SECTOR_METADATA_PATH = Path(str(sector_cfg.get("metadata_path", SECTOR_METADATA_PATH)))
        SECTOR_SYMBOL_COLUMN = str(sector_cfg.get("symbol_column", SECTOR_SYMBOL_COLUMN))
        SECTOR_COLUMN = str(sector_cfg.get("sector_column", SECTOR_COLUMN))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Enhanced quantum regime evaluator")
    parser.add_argument("--config", type=str, default=str(DEFAULT_CONFIG_PATH), help="Path to JSON config")
    parser.add_argument("--k", type=int, default=None, help="Override portfolio size K")
    parser.add_argument("--seed", type=int, default=None, help="Override base seed")
    parser.add_argument("--min-train-coverage", type=float, default=None, help="Override min train coverage [0,1]")
    parser.add_argument("--min-test-points", type=int, default=None, help="Override minimum test points")
    parser.add_argument("--skip-walkforward", action="store_true", help="Skip rolling walk-forward block")
    parser.add_argument("--disable-artifacts", action="store_true", help="Disable per-scenario artifact JSON export")
    parser.add_argument("--artifacts-dir", type=str, default=None, help="Override artifacts output directory")
    parser.add_argument("--disable-sector-cap", action="store_true", help="Disable sector weight cap post-processing")
    parser.add_argument("--sector-cap", type=float, default=None, help="Override max sector weight cap in (0,1]")
    return parser.parse_args()


def sanitize_name(name: str) -> str:
    """Convert arbitrary scenario names into filesystem-safe folder names."""
    cleaned = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in name)
    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")
    return cleaned.strip("_") or "scenario"


def to_serializable(value):
    """Recursively convert numpy/pandas values to JSON-serializable Python types."""
    if isinstance(value, dict):
        return {k: to_serializable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [to_serializable(v) for v in value]
    if isinstance(value, tuple):
        return [to_serializable(v) for v in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()
    return value


def matrix_stats(matrix: np.ndarray) -> dict:
    """Compact numeric summary for matrices/vectors used in optimization."""
    arr = np.asarray(matrix)
    return {
        "shape": [int(x) for x in arr.shape],
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
        "mean": float(np.mean(arr)),
        "std": float(np.std(arr)),
    }


def load_sector_map() -> Dict[str, str]:
    """Load symbol to sector mapping for sector-aware post-processing."""
    if not SECTOR_METADATA_PATH.exists():
        print(f"Sector metadata not found: {SECTOR_METADATA_PATH}. Sector cap disabled.")
        return {}

    df = pd.read_csv(SECTOR_METADATA_PATH)
    if SECTOR_SYMBOL_COLUMN not in df.columns or SECTOR_COLUMN not in df.columns:
        print(
            "Sector metadata columns missing. "
            f"Required: {SECTOR_SYMBOL_COLUMN}, {SECTOR_COLUMN}. Sector cap disabled."
        )
        return {}

    mapping = {}
    for _, row in df[[SECTOR_SYMBOL_COLUMN, SECTOR_COLUMN]].dropna().iterrows():
        symbol = str(row[SECTOR_SYMBOL_COLUMN]).strip()
        sector = str(row[SECTOR_COLUMN]).strip()
        if symbol:
            mapping[symbol] = sector or "Unknown"
    return mapping


def sector_weight_breakdown(weights: Dict[str, float], sector_map: Dict[str, str]) -> Dict[str, float]:
    """Aggregate stock-level weights into sector-level weights."""
    out: Dict[str, float] = {}
    for stock, weight in weights.items():
        sector = sector_map.get(stock, "Unknown")
        out[sector] = out.get(sector, 0.0) + float(weight)
    return out


def apply_sector_weight_cap(
    weights: Dict[str, float],
    sector_map: Dict[str, str],
    max_sector_weight: float,
) -> Tuple[Dict[str, float], dict]:
    """Cap aggregate sector weights and redistribute excess across uncapped sectors."""
    if not weights:
        return weights, {"applied": False, "reason": "empty_weights"}

    total = sum(float(v) for v in weights.values())
    if total <= 0:
        return weights, {"applied": False, "reason": "non_positive_total"}

    working = {k: float(v) / total for k, v in weights.items()}

    mapped = [s for s in working if s in sector_map]
    if len(mapped) < len(working):
        return working, {
            "applied": False,
            "reason": "incomplete_sector_mapping",
            "mapped_stocks": int(len(mapped)),
            "total_stocks": int(len(working)),
            "coverage": float(len(mapped) / len(working)) if len(working) else 0.0,
        }

    before = sector_weight_breakdown(working, sector_map)

    if max_sector_weight <= 0 or max_sector_weight >= 1:
        return working, {
            "applied": False,
            "reason": "invalid_or_unnecessary_cap",
            "sector_weights_before": before,
            "sector_weights_after": before,
        }

    capped = working.copy()
    sector_to_stocks: Dict[str, List[str]] = {}
    for stock in capped:
        sector = sector_map.get(stock, "Unknown")
        sector_to_stocks.setdefault(sector, []).append(stock)

    excess = 0.0
    for sector, stocks in sector_to_stocks.items():
        sec_sum = sum(capped[s] for s in stocks)
        if sec_sum > max_sector_weight:
            scale = max_sector_weight / sec_sum
            for s in stocks:
                capped[s] *= scale
            excess += sec_sum - max_sector_weight

    if excess > 0:
        capacities: Dict[str, float] = {}
        for sector, stocks in sector_to_stocks.items():
            sec_sum = sum(capped[s] for s in stocks)
            capacities[sector] = max(0.0, max_sector_weight - sec_sum)

        total_capacity = sum(capacities.values())
        if total_capacity > 0:
            for sector, stocks in sector_to_stocks.items():
                if capacities[sector] <= 0:
                    continue
                sector_add = excess * (capacities[sector] / total_capacity)
                base = [capped[s] for s in stocks]
                base_total = sum(base)
                if base_total <= 0:
                    split = sector_add / len(stocks)
                    for s in stocks:
                        capped[s] += split
                else:
                    for s in stocks:
                        capped[s] += sector_add * (capped[s] / base_total)

    final_total = sum(capped.values())
    if final_total > 0:
        capped = {k: v / final_total for k, v in capped.items()}

    after = sector_weight_breakdown(capped, sector_map)
    max_after = max(after.values()) if after else 0.0

    return capped, {
        "applied": True,
        "max_sector_weight": float(max_sector_weight),
        "sector_weights_before": before,
        "sector_weights_after": after,
        "max_sector_after": float(max_after),
        "constraint_satisfied": bool(max_after <= max_sector_weight + 1e-6),
    }


def get_train_stats_for_selected(
    prices_df: pd.DataFrame,
    selected_stocks: List[str],
    train_start: str,
    train_end: str,
) -> dict:
    """Compute train-period return/covariance artifacts for selected stocks."""
    mask = (prices_df["Date"] >= train_start) & (prices_df["Date"] <= train_end)
    train_df = prices_df[mask]
    stock_prices = train_df[selected_stocks].ffill().bfill()
    returns = stock_prices.pct_change().dropna()

    if len(returns) == 0:
        return {
            "train_rows": int(len(train_df)),
            "returns_rows": 0,
            "mean_returns_annualized": [],
            "covariance_annualized": [],
            "covariance_stats": None,
        }

    mean_returns = (returns.mean() * 252).values
    covariance = (returns.cov() * 252).values

    return {
        "train_rows": int(len(train_df)),
        "returns_rows": int(len(returns)),
        "mean_returns_annualized": mean_returns.tolist(),
        "covariance_annualized": covariance.tolist(),
        "covariance_stats": matrix_stats(covariance),
    }


def save_scenario_artifact(artifact_dir: Path, scenario_payload: dict) -> str:
    """Persist detailed scenario internals as JSON artifact."""
    artifact_dir.mkdir(parents=True, exist_ok=True)
    out_file = artifact_dir / "scenario_artifact.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(to_serializable(scenario_payload), f, indent=2)
    return str(out_file)


def get_train_eligible_stocks(
    prices_df: pd.DataFrame,
    train_start: str,
    train_end: str,
    test_start: str,
    test_end: str,
    min_train_coverage: float = MIN_TRAIN_COVERAGE,
    min_test_points: int = MIN_TEST_POINTS,
) -> List[str]:
    """Filter stocks by train-period sufficiency, then enforce basic test availability."""
    train_mask = (prices_df["Date"] >= train_start) & (prices_df["Date"] <= train_end)
    test_mask = (prices_df["Date"] >= test_start) & (prices_df["Date"] <= test_end)

    train_df = prices_df[train_mask]
    test_df = prices_df[test_mask]

    if len(train_df) == 0 or len(test_df) == 0:
        return []

    min_train_points = int(len(train_df) * min_train_coverage)

    eligible = []
    for col in prices_df.columns:
        if col == "Date":
            continue
        train_non_null = train_df[col].notna().sum()
        test_non_null = test_df[col].notna().sum()
        if train_non_null >= min_train_points and test_non_null >= min_test_points:
            eligible.append(col)

    return eligible


def stable_seed(base_seed: int, name: str, offset: int = 0) -> int:
    """Create deterministic seed from scenario name."""
    checksum = sum(ord(ch) for ch in name)
    return base_seed + checksum + offset


def pick_winners(results: Dict[str, dict]) -> Tuple[str, str]:
    """Pick winners by total return and Sharpe."""
    by_return = max(results.items(), key=lambda kv: kv[1]["total_return"])[0]
    by_sharpe = max(results.items(), key=lambda kv: kv[1]["sharpe"])[0]
    return by_return, by_sharpe


def evaluate_one_scenario(
    scenario_name: str,
    cfg: dict,
    prices_df: pd.DataFrame,
    k_stocks: int = K_STOCKS,
    base_seed: int = BASE_SEED,
    sector_map: Dict[str, str] | None = None,
    artifact_root: Path | None = None,
) -> dict:
    """Run one scenario with deterministic quantum seed and strict train filtering."""
    if k_stocks <= 0:
        raise ValueError(f"k_stocks must be >= 1, got {k_stocks}")

    print("\n" + "=" * 90)
    print(f"SCENARIO: {scenario_name}")
    print("=" * 90)
    print(cfg["description"])

    validate_no_data_leakage(
        cfg["train_start"],
        cfg["train_end"],
        cfg["test_start"],
        cfg["test_end"],
    )

    eligible_stocks = get_train_eligible_stocks(
        prices_df,
        cfg["train_start"],
        cfg["train_end"],
        cfg["test_start"],
        cfg["test_end"],
    )

    print(
        f"Eligible stocks (train coverage >= {MIN_TRAIN_COVERAGE:.0%}, "
        f"test points >= {MIN_TEST_POINTS}): {len(eligible_stocks)}"
    )

    if len(eligible_stocks) < k_stocks:
        raise ValueError(
            f"Not enough eligible stocks ({len(eligible_stocks)}) for K={k_stocks}"
        )

    results = {}
    strategy_details = {}

    sector_cap_active = bool(SECTOR_CONSTRAINTS_ENABLED and sector_map)

    q_seed = stable_seed(base_seed, scenario_name, offset=1)
    quantum_stocks, quantum_internal = select_quantum_portfolio(
        prices_df,
        eligible_stocks,
        cfg["train_start"],
        cfg["train_end"],
        K=k_stocks,
        seed=q_seed,
        return_details=True,
        include_matrices=INCLUDE_FULL_QUBO_MATRIX,
    )
    quantum_weights, quantum_train_sharpe, quantum_opt_info = optimize_weights(
        quantum_stocks,
        prices_df,
        cfg["train_start"],
        cfg["train_end"],
        return_info=True,
    )
    quantum_sector_info = {"applied": False, "reason": "sector_cap_disabled"}
    if sector_cap_active:
        quantum_weights, quantum_sector_info = apply_sector_weight_cap(
            quantum_weights,
            sector_map,
            MAX_SECTOR_WEIGHT,
        )
    q_metrics = backtest_period(
        prices_df,
        quantum_stocks,
        quantum_weights,
        cfg["test_start"],
        cfg["test_end"],
    )
    if q_metrics is None:
        raise ValueError("Quantum backtest returned no test data")
    results["Quantum"] = q_metrics
    strategy_details["Quantum"] = {
        "selected_stocks": quantum_stocks,
        "weights": quantum_weights,
        "train_sharpe": float(quantum_train_sharpe),
        "optimization_info": quantum_opt_info,
        "sector_info": quantum_sector_info,
        "selection_internal": {
            "train_start": quantum_internal["train_start"],
            "train_end": quantum_internal["train_end"],
            "train_rows": quantum_internal["train_rows"],
            "returns_rows": quantum_internal["returns_rows"],
            "stock_symbols": quantum_internal["stock_symbols"],
            "mean_returns_stats": matrix_stats(np.asarray(quantum_internal["mean_returns_full"])),
            "covariance_stats": matrix_stats(np.asarray(quantum_internal["covariance_full"])),
            "qubo": quantum_internal["qubo"],
        },
    }

    greedy_stocks = select_greedy_portfolio(
        prices_df,
        eligible_stocks,
        cfg["train_start"],
        cfg["train_end"],
        K=k_stocks,
    )
    greedy_weights, greedy_train_sharpe, greedy_opt_info = optimize_weights(
        greedy_stocks,
        prices_df,
        cfg["train_start"],
        cfg["train_end"],
        return_info=True,
    )
    greedy_sector_info = {"applied": False, "reason": "sector_cap_disabled"}
    if sector_cap_active:
        greedy_weights, greedy_sector_info = apply_sector_weight_cap(
            greedy_weights,
            sector_map,
            MAX_SECTOR_WEIGHT,
        )
    g_metrics = backtest_period(
        prices_df,
        greedy_stocks,
        greedy_weights,
        cfg["test_start"],
        cfg["test_end"],
    )
    if g_metrics is None:
        raise ValueError("Greedy backtest returned no test data")
    results["Greedy"] = g_metrics
    strategy_details["Greedy"] = {
        "selected_stocks": greedy_stocks,
        "weights": greedy_weights,
        "train_sharpe": float(greedy_train_sharpe),
        "optimization_info": greedy_opt_info,
        "sector_info": greedy_sector_info,
        "selection_internal": get_train_stats_for_selected(
            prices_df,
            greedy_stocks,
            cfg["train_start"],
            cfg["train_end"],
        ),
    }

    classical_stocks = select_classical_portfolio(
        prices_df,
        eligible_stocks,
        cfg["train_start"],
        cfg["train_end"],
        K=k_stocks,
    )
    classical_weights, classical_train_sharpe, classical_opt_info = optimize_weights(
        classical_stocks,
        prices_df,
        cfg["train_start"],
        cfg["train_end"],
        return_info=True,
    )
    classical_sector_info = {"applied": False, "reason": "sector_cap_disabled"}
    if sector_cap_active:
        classical_weights, classical_sector_info = apply_sector_weight_cap(
            classical_weights,
            sector_map,
            MAX_SECTOR_WEIGHT,
        )
    c_metrics = backtest_period(
        prices_df,
        classical_stocks,
        classical_weights,
        cfg["test_start"],
        cfg["test_end"],
    )
    if c_metrics is None:
        raise ValueError("Classical backtest returned no test data")
    results["Classical MVO"] = c_metrics
    strategy_details["Classical MVO"] = {
        "selected_stocks": classical_stocks,
        "weights": classical_weights,
        "train_sharpe": float(classical_train_sharpe),
        "optimization_info": classical_opt_info,
        "sector_info": classical_sector_info,
        "selection_internal": get_train_stats_for_selected(
            prices_df,
            classical_stocks,
            cfg["train_start"],
            cfg["train_end"],
        ),
    }

    winner_return, winner_sharpe = pick_winners(results)

    print("-" * 90)
    print(f"{'Strategy':<20} {'Return %':>11} {'Max DD %':>11} {'Sharpe':>9} {'VaR95 %':>9}")
    print("-" * 90)
    for strategy, m in results.items():
        print(
            f"{strategy:<20} {m['total_return']:>10.2f}% {m['max_drawdown']:>10.2f}% "
            f"{m['sharpe']:>9.3f} {m['var_95']:>8.2f}%"
        )
    print(f"Winner by Return: {winner_return}")
    print(f"Winner by Sharpe: {winner_sharpe}")

    artifact_file = None
    if artifact_root is not None and ARTIFACTS_ENABLED:
        scenario_artifact = {
            "scenario": scenario_name,
            "meta": {
                "description": cfg["description"],
                "regime": cfg["regime"],
                "train_start": cfg["train_start"],
                "train_end": cfg["train_end"],
                "test_start": cfg["test_start"],
                "test_end": cfg["test_end"],
                "eligible_stocks": len(eligible_stocks),
                "eligible_stock_list": eligible_stocks,
                "k_stocks": int(k_stocks),
                "quantum_seed": q_seed,
                "sector_constraints": {
                    "enabled": sector_cap_active,
                    "max_sector_weight": float(MAX_SECTOR_WEIGHT),
                    "metadata_path": str(SECTOR_METADATA_PATH),
                    "symbol_column": SECTOR_SYMBOL_COLUMN,
                    "sector_column": SECTOR_COLUMN,
                },
            },
            "strategy_details": strategy_details,
            "results": {
                strategy: {
                    "total_return": metrics["total_return"],
                    "volatility": metrics["volatility"],
                    "max_drawdown": metrics["max_drawdown"],
                    "var_95": metrics["var_95"],
                    "sharpe": metrics["sharpe"],
                }
                for strategy, metrics in results.items()
            },
            "winner_by_return": winner_return,
            "winner_by_sharpe": winner_sharpe,
        }
        scenario_dir = artifact_root / sanitize_name(scenario_name)
        artifact_file = save_scenario_artifact(scenario_dir, scenario_artifact)

    return {
        "meta": {
            "description": cfg["description"],
            "regime": cfg["regime"],
            "train_start": cfg["train_start"],
            "train_end": cfg["train_end"],
            "test_start": cfg["test_start"],
            "test_end": cfg["test_end"],
            "eligible_stocks": len(eligible_stocks),
            "quantum_seed": q_seed,
            "artifact_file": artifact_file,
            "sector_constraints_enabled": sector_cap_active,
            "max_sector_weight": float(MAX_SECTOR_WEIGHT),
        },
        "results": {
            strategy: {
                "total_return": metrics["total_return"],
                "volatility": metrics["volatility"],
                "max_drawdown": metrics["max_drawdown"],
                "var_95": metrics["var_95"],
                "sharpe": metrics["sharpe"],
            }
            for strategy, metrics in results.items()
        },
        "winner_by_return": winner_return,
        "winner_by_sharpe": winner_sharpe,
    }


def build_walkforward_scenarios(prices_df: pd.DataFrame) -> Dict[str, dict]:
    """Build rolling walk-forward scenarios from 2020 to latest date.

    Setup from runtime config globals:
    - train window: WF_TRAIN_MONTHS
    - test window: WF_TEST_MONTHS
    - step size: WF_STEP_MONTHS
    """
    latest_date = prices_df["Date"].max()
    start_test = pd.Timestamp(WF_START_TEST)

    scenarios = {}
    idx = 1
    cur_test_start = start_test

    while cur_test_start <= latest_date - pd.Timedelta(days=WF_MIN_REMAINING_DAYS):
        train_end = cur_test_start - pd.Timedelta(days=1)
        train_start = train_end - pd.DateOffset(months=WF_TRAIN_MONTHS)
        test_end = min(cur_test_start + pd.DateOffset(months=WF_TEST_MONTHS) - pd.Timedelta(days=1), latest_date)

        name = f"WF_{idx:02d}_{cur_test_start.date()}_to_{test_end.date()}"
        scenarios[name] = {
            "train_start": str(train_start.date()),
            "train_end": str(train_end.date()),
            "test_start": str(cur_test_start.date()),
            "test_end": str(test_end.date()),
            "description": "Rolling walk-forward 12M train + 6M test",
            "regime": "Normal",  # Walk-forward treated as regular regime bucket
        }

        idx += 1
        cur_test_start = cur_test_start + pd.DateOffset(months=WF_STEP_MONTHS)

    return scenarios


def aggregate_winner_counts(scenario_outputs: Dict[str, dict]) -> dict:
    strategies = ["Quantum", "Greedy", "Classical MVO"]
    regimes = ["Crash", "Normal", "Present"]

    by_return = {r: {s: 0 for s in strategies} for r in regimes}
    by_sharpe = {r: {s: 0 for s in strategies} for r in regimes}

    for _, payload in scenario_outputs.items():
        regime = payload["meta"]["regime"]
        win_r = payload["winner_by_return"]
        win_s = payload["winner_by_sharpe"]
        if regime in by_return and win_r in by_return[regime]:
            by_return[regime][win_r] += 1
        if regime in by_sharpe and win_s in by_sharpe[regime]:
            by_sharpe[regime][win_s] += 1

    return {
        "winner_counts_by_return": by_return,
        "winner_counts_by_sharpe": by_sharpe,
    }


def run_all(include_walkforward: bool = True) -> dict:
    prices_df = load_complete_data()
    sector_map = load_sector_map() if SECTOR_CONSTRAINTS_ENABLED else {}

    artifact_root = None
    if ARTIFACTS_ENABLED:
        artifact_root = ARTIFACTS_OUTPUT_DIR
        artifact_root.mkdir(parents=True, exist_ok=True)

    outputs = {}

    # Fixed scenarios by user-requested regimes
    for category, scenario_dict in REGIME_SCENARIOS.items():
        print("\n" + "#" * 90)
        print(f"CATEGORY: {category}")
        print("#" * 90)
        for name, cfg in scenario_dict.items():
            outputs[name] = evaluate_one_scenario(
                name,
                cfg,
                prices_df,
                sector_map=sector_map,
                artifact_root=artifact_root,
            )

    # Walk-forward robustness from configured start onward
    if include_walkforward:
        walkforward = build_walkforward_scenarios(prices_df)
        print("\n" + "#" * 90)
        print(f"CATEGORY: Rolling Walk-Forward ({WF_START_TEST} to {prices_df['Date'].max().date()})")
        print("#" * 90)
        for name, cfg in walkforward.items():
            outputs[name] = evaluate_one_scenario(
                name,
                cfg,
                prices_df,
                sector_map=sector_map,
                artifact_root=artifact_root,
            )

    summary = aggregate_winner_counts(outputs)

    report = {
        "config": {
            "base_seed": BASE_SEED,
            "k_stocks": K_STOCKS,
            "min_train_coverage": MIN_TRAIN_COVERAGE,
            "min_test_points": MIN_TEST_POINTS,
            "walkforward": {
                "start_test": WF_START_TEST,
                "train_months": WF_TRAIN_MONTHS,
                "test_months": WF_TEST_MONTHS,
                "step_months": WF_STEP_MONTHS,
                "min_remaining_days": WF_MIN_REMAINING_DAYS,
            },
            "artifacts": {
                "enabled": ARTIFACTS_ENABLED,
                "output_dir": str(ARTIFACTS_OUTPUT_DIR),
                "include_full_qubo_matrix": INCLUDE_FULL_QUBO_MATRIX,
            },
            "sector_constraints": {
                "enabled": SECTOR_CONSTRAINTS_ENABLED,
                "max_sector_weight": MAX_SECTOR_WEIGHT,
                "metadata_path": str(SECTOR_METADATA_PATH),
                "symbol_column": SECTOR_SYMBOL_COLUMN,
                "sector_column": SECTOR_COLUMN,
                "mapped_symbols": len(sector_map),
            },
            "include_walkforward": include_walkforward,
        },
        "scenarios": outputs,
        "summary": summary,
    }

    return report


def main():
    args = parse_args()

    config_data = load_runtime_config(Path(args.config))
    apply_runtime_config(config_data)

    # CLI overrides (highest priority)
    global BASE_SEED, K_STOCKS, MIN_TRAIN_COVERAGE, MIN_TEST_POINTS
    global ARTIFACTS_ENABLED, ARTIFACTS_OUTPUT_DIR
    global SECTOR_CONSTRAINTS_ENABLED, MAX_SECTOR_WEIGHT
    if args.seed is not None:
        BASE_SEED = int(args.seed)
    if args.k is not None:
        K_STOCKS = int(args.k)
    if args.min_train_coverage is not None:
        MIN_TRAIN_COVERAGE = float(args.min_train_coverage)
    if args.min_test_points is not None:
        MIN_TEST_POINTS = int(args.min_test_points)
    if args.disable_artifacts:
        ARTIFACTS_ENABLED = False
    if args.artifacts_dir is not None:
        ARTIFACTS_OUTPUT_DIR = Path(args.artifacts_dir)
    if args.disable_sector_cap:
        SECTOR_CONSTRAINTS_ENABLED = False
    if args.sector_cap is not None:
        MAX_SECTOR_WEIGHT = float(args.sector_cap)

    if K_STOCKS <= 0:
        raise ValueError(f"k_stocks must be >= 1, got {K_STOCKS}")
    if not 0 < MIN_TRAIN_COVERAGE <= 1:
        raise ValueError(f"min_train_coverage must be in (0,1], got {MIN_TRAIN_COVERAGE}")
    if MIN_TEST_POINTS <= 0:
        raise ValueError(f"min_test_points must be >= 1, got {MIN_TEST_POINTS}")
    if SECTOR_CONSTRAINTS_ENABLED and not 0 < MAX_SECTOR_WEIGHT <= 1:
        raise ValueError(f"sector_cap must be in (0,1], got {MAX_SECTOR_WEIGHT}")

    report = run_all(include_walkforward=not args.skip_walkforward)

    out_dir = Path("results")
    out_dir.mkdir(exist_ok=True)

    out_file = out_dir / "enhanced_regime_comparison_report.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print("\n" + "=" * 90)
    print("FINAL REGIME WINNER COUNTS")
    print("=" * 90)
    print(json.dumps(report["summary"], indent=2))
    print(f"\nSaved report: {out_file}")


if __name__ == "__main__":
    main()
