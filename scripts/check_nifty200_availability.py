#!/usr/bin/env python3
"""
Check NIFTY200 universe availability against dataset and scenario windows.

Outputs:
- results/nifty200_availability_check.json
- results/nifty200_availability_check.md
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set

import pandas as pd


ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "unified_compare_config.json"


def load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_symbols_from_file(base_dir: Path, rel_path: str) -> List[str]:
    p = (base_dir / rel_path).resolve()
    if not p.exists():
        raise FileNotFoundError(f"Symbol file not found: {p}")

    if p.suffix.lower() == ".json":
        data = load_json(p)
        if isinstance(data, list):
            return [str(v).strip() for v in data if str(v).strip()]
        if isinstance(data, dict):
            out: List[str] = []
            for value in data.values():
                if isinstance(value, list):
                    out.extend(str(v).strip() for v in value if str(v).strip())
            return out
        raise ValueError(f"Unsupported JSON symbol schema: {p}")

    df = pd.read_csv(p)
    col_lookup = {str(c).strip().lower(): c for c in df.columns}
    if "symbol" in col_lookup:
        col = col_lookup["symbol"]
    elif "stock" in col_lookup:
        col = col_lookup["stock"]
    elif "ticker" in col_lookup:
        col = col_lookup["ticker"]
    else:
        col = df.columns[0]

    return [str(v).strip() for v in df[col].dropna().tolist() if str(v).strip()]


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
        raise FileNotFoundError("No valid dataset found in candidates")

    profiles.sort(key=lambda x: (x["end_ts"], x["rows"], x["assets"]), reverse=True)
    return profiles[0]


def build_horizon_scenarios(end_ts, horizon_months: List[int], train_map: Dict[str, int]):
    scenarios = {}
    for test_m in horizon_months:
        train_m = int(train_map.get(str(test_m), test_m))
        test_end = pd.to_datetime(end_ts)
        test_start = (test_end - pd.DateOffset(months=test_m) + pd.Timedelta(days=1)).normalize()
        train_end = (test_start - pd.Timedelta(days=1)).normalize()
        train_start = (train_end - pd.DateOffset(months=train_m) + pd.Timedelta(days=1)).normalize()
        name = f"Horizon_{test_m}M_Train_{train_m}M"
        scenarios[name] = {
            "train_start": str(train_start.date()),
            "train_end": str(train_end.date()),
            "test_start": str(test_start.date()),
            "test_end": str(test_end.date()),
        }
    return scenarios


def evaluate_window(
    prices_df: pd.DataFrame,
    symbols: List[str],
    train_start: str,
    train_end: str,
    test_start: str,
    test_end: str,
    min_train_coverage: float,
    min_test_points: int,
    min_train_points: int,
    min_return_points: int,
):
    train_mask = (prices_df["Date"] >= train_start) & (prices_df["Date"] <= train_end)
    test_mask = (prices_df["Date"] >= test_start) & (prices_df["Date"] <= test_end)

    train_df = prices_df.loc[train_mask]
    test_df = prices_df.loc[test_mask]

    total_train = len(train_df)
    min_required_coverage = int(total_train * float(min_train_coverage))

    present_cols = [c for c in symbols if c in prices_df.columns]
    missing_in_dataset = sorted([s for s in symbols if s not in prices_df.columns])

    eligible: List[str] = []
    ineligible: List[str] = []

    for s in present_cols:
        train_non_null = int(train_df[s].notna().sum())
        test_non_null = int(test_df[s].notna().sum())

        if train_non_null < min_required_coverage:
            ineligible.append(s)
            continue
        if test_non_null < int(min_test_points):
            ineligible.append(s)
            continue
        if int(min_train_points) > 0 and train_non_null < int(min_train_points):
            ineligible.append(s)
            continue

        series_train = train_df[s].ffill().bfill()
        returns_train = series_train.pct_change().replace([float("inf"), float("-inf")], pd.NA).dropna()

        if int(min_return_points) > 0 and len(returns_train) < int(min_return_points):
            ineligible.append(s)
            continue
        if len(returns_train) == 0:
            ineligible.append(s)
            continue

        variance = float(pd.Series(returns_train).var())
        if not pd.notna(variance) or variance <= 0:
            ineligible.append(s)
            continue

        eligible.append(s)

    return {
        "train_start": train_start,
        "train_end": train_end,
        "test_start": test_start,
        "test_end": test_end,
        "total_symbols_requested": len(symbols),
        "present_in_dataset_count": len(present_cols),
        "missing_in_dataset_count": len(missing_in_dataset),
        "missing_in_dataset": missing_in_dataset,
        "eligible_count": len(eligible),
        "ineligible_count": len(ineligible),
        "eligible_symbols": sorted(eligible),
        "ineligible_symbols": sorted(ineligible),
    }


def main() -> int:
    cfg = load_json(CONFIG_PATH)
    eval_cfg = cfg.get("evaluation", {})

    dataset = choose_best_dataset(ROOT, cfg.get("dataset_candidates", []))
    prices_df = pd.read_csv(dataset["path"], parse_dates=["Date"]).sort_values("Date")

    universe_cfg = cfg.get("universe_filter", {})
    symbol_rel = universe_cfg.get("custom_symbols_path", "Dataset/ind_nifty200list.csv")
    symbols = sorted(list(set(load_symbols_from_file(ROOT, symbol_rel))))

    asset_cols = [c for c in prices_df.columns if c != "Date"]
    present_global = sorted([s for s in symbols if s in asset_cols])
    missing_global = sorted([s for s in symbols if s not in asset_cols])

    min_train_cov_h = float(eval_cfg.get("min_train_coverage_horizon", eval_cfg.get("min_train_coverage", 0.8)))
    min_train_cov_c = float(eval_cfg.get("min_train_coverage_crash", eval_cfg.get("min_train_coverage", 0.8)))
    min_test_h = int(eval_cfg.get("min_test_points_horizon", eval_cfg.get("min_test_points", 20)))
    min_test_c = int(eval_cfg.get("min_test_points_crash", eval_cfg.get("min_test_points", 20)))
    min_train_points_h = int(eval_cfg.get("min_train_points_horizon", eval_cfg.get("min_train_points", 0)))
    min_train_points_c = int(eval_cfg.get("min_train_points_crash", eval_cfg.get("min_train_points", 0)))
    min_return_points_h = int(eval_cfg.get("min_return_points_horizon", eval_cfg.get("min_return_points", 0)))
    min_return_points_c = int(eval_cfg.get("min_return_points_crash", eval_cfg.get("min_return_points", 0)))

    horizon_scenarios = build_horizon_scenarios(
        dataset["end_ts"],
        eval_cfg.get("horizon_months", [6, 12, 24, 36]),
        eval_cfg.get("train_months_by_horizon", {}),
    )

    crash_scenarios = cfg.get("crash_scenarios", {})

    horizon_out = {}
    for name, sc in horizon_scenarios.items():
        horizon_out[name] = evaluate_window(
            prices_df,
            symbols,
            sc["train_start"],
            sc["train_end"],
            sc["test_start"],
            sc["test_end"],
            min_train_cov_h,
            min_test_h,
            min_train_points_h,
            min_return_points_h,
        )

    crash_out = {}
    for name, sc in crash_scenarios.items():
        crash_out[name] = evaluate_window(
            prices_df,
            symbols,
            sc["train_start"],
            sc["train_end"],
            sc["test_start"],
            sc["test_end"],
            min_train_cov_c,
            min_test_c,
            min_train_points_c,
            min_return_points_c,
        )

    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "dataset": {
            "path": dataset["path"],
            "rows": dataset["rows"],
            "assets": dataset["assets"],
            "start": dataset["start"],
            "end": dataset["end"],
        },
        "symbol_source": symbol_rel,
        "requested_symbol_count": len(symbols),
        "present_symbols_count": len(present_global),
        "missing_symbols_count": len(missing_global),
        "present_symbols": present_global,
        "missing_symbols": missing_global,
        "thresholds": {
            "horizon": {
                "min_train_coverage": min_train_cov_h,
                "min_test_points": min_test_h,
                "min_train_points": min_train_points_h,
                "min_return_points": min_return_points_h,
            },
            "crash": {
                "min_train_coverage": min_train_cov_c,
                "min_test_points": min_test_c,
                "min_train_points": min_train_points_c,
                "min_return_points": min_return_points_c,
            },
        },
        "horizon_windows": horizon_out,
        "crash_windows": crash_out,
    }

    results_dir = ROOT / "results"
    results_dir.mkdir(exist_ok=True)

    json_path = results_dir / "nifty200_availability_check.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    md_lines = [
        "# NIFTY200 Availability Check",
        "",
        f"Generated: {report['generated_at']}",
        "",
        "## Dataset",
        "",
        f"- Path: {report['dataset']['path']}",
        f"- Rows: {report['dataset']['rows']}",
        f"- Assets: {report['dataset']['assets']}",
        f"- Date range: {report['dataset']['start']} to {report['dataset']['end']}",
        "",
        "## Global Symbols",
        "",
        f"- Requested symbols: {report['requested_symbol_count']}",
        f"- Present in dataset: {report['present_symbols_count']}",
        f"- Missing in dataset: {report['missing_symbols_count']}",
        "",
        "## Effective Usable Counts",
        "",
        "### Horizon",
        "",
        "| Scenario | Eligible | Present | Missing |",
        "|---|---:|---:|---:|",
    ]

    for name, w in horizon_out.items():
        md_lines.append(
            f"| {name} | {w['eligible_count']} | {w['present_in_dataset_count']} | {w['missing_in_dataset_count']} |"
        )

    md_lines.extend([
        "",
        "### Crash",
        "",
        "| Scenario | Eligible | Present | Missing |",
        "|---|---:|---:|---:|",
    ])

    for name, w in crash_out.items():
        md_lines.append(
            f"| {name} | {w['eligible_count']} | {w['present_in_dataset_count']} | {w['missing_in_dataset_count']} |"
        )

    md_path = results_dir / "nifty200_availability_check.md"
    md_path.write_text("\n".join(md_lines), encoding="utf-8")

    print(f"Saved: {json_path}")
    print(f"Saved: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
