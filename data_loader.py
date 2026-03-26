from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import json
import re

import pandas as pd


@dataclass
class DataBundle:
    asset_prices: pd.DataFrame
    benchmark_prices: pd.DataFrame
    sector_map: Dict[str, str]
    discovered_files: Dict[str, List[str]]


def _read_csv_with_date(path: Path) -> Optional[pd.DataFrame]:
    try:
        df = pd.read_csv(path)
    except Exception:
        return None

    date_col = None
    for c in df.columns:
        if str(c).strip().lower() == "date":
            date_col = c
            break
    if date_col is None:
        return None

    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df = df.dropna(subset=[date_col]).sort_values(date_col)
    df = df.rename(columns={date_col: "Date"}).set_index("Date")
    return df


def _is_wide_price_panel(df: pd.DataFrame) -> bool:
    if df is None or df.empty:
        return False
    return ("Close" not in df.columns) and (len(df.columns) > 20)


def _extract_close_series(df: pd.DataFrame) -> Optional[pd.Series]:
    if df is None or df.empty:
        return None

    close_candidates = [c for c in df.columns if str(c).strip().lower() == "close"]
    if close_candidates:
        ser = pd.to_numeric(df[close_candidates[0]], errors="coerce")
        ser.name = "Close"
        return ser

    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    if len(numeric_cols) == 1:
        ser = pd.to_numeric(df[numeric_cols[0]], errors="coerce")
        ser.name = "Close"
        return ser

    return None


def _benchmark_name_from_file(path: Path) -> str:
    stem = path.stem
    cleaned = re.sub(r"_\d{4}_to_\d{4}", "", stem, flags=re.IGNORECASE)
    cleaned = cleaned.replace("__", "_")
    return cleaned


def _load_sector_map(root: Path) -> Dict[str, str]:
    sector_map: Dict[str, str] = {}

    # Discover CSV metadata files with Symbol/Industry columns.
    for csv_path in root.glob("*.csv"):
        try:
            df = pd.read_csv(csv_path)
        except Exception:
            continue
        cols = {c.lower().strip(): c for c in df.columns}
        sym_col = cols.get("symbol")
        ind_col = cols.get("industry")
        if sym_col and ind_col:
            for _, row in df[[sym_col, ind_col]].dropna().iterrows():
                sector_map[str(row[sym_col]).strip().upper()] = str(row[ind_col]).strip()

    # Discover JSON metadata files with {group: [symbols]} style mappings.
    for json_path in root.glob("*.json"):
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
        except Exception:
            continue

        if not isinstance(data, dict):
            continue

        def absorb_mapping(mapping: dict) -> None:
            for sector, symbols in mapping.items():
                if not isinstance(symbols, list):
                    continue
                clean_sector = str(sector).replace("_", " ").strip()
                for s in symbols:
                    if isinstance(s, str):
                        sector_map.setdefault(s.strip().upper(), clean_sector)

        absorb_mapping(data)
        for v in data.values():
            if isinstance(v, dict):
                absorb_mapping(v)

    return sector_map


def load_all_data(root_dir: str | Path) -> DataBundle:
    root = Path(root_dir)
    csv_files = sorted(root.glob("*.csv"))

    discovered = {
        "all_csv": [p.name for p in csv_files],
        "wide_panels": [],
        "benchmarks": [],
        "ignored": [],
    }

    asset_prices: Optional[pd.DataFrame] = None
    benchmark_series: Dict[str, pd.Series] = {}

    for path in csv_files:
        df = _read_csv_with_date(path)
        if df is None:
            discovered["ignored"].append(path.name)
            continue

        if _is_wide_price_panel(df):
            panel = df.apply(pd.to_numeric, errors="coerce")
            panel = panel.dropna(axis=1, how="all")
            discovered["wide_panels"].append(path.name)
            if asset_prices is None or panel.shape[1] > asset_prices.shape[1]:
                asset_prices = panel
            continue

        close_ser = _extract_close_series(df)
        if close_ser is not None:
            name = _benchmark_name_from_file(path)
            benchmark_series[name] = close_ser
            discovered["benchmarks"].append(path.name)
        else:
            discovered["ignored"].append(path.name)

    if asset_prices is None:
        raise RuntimeError("No wide asset price panel found in workspace.")

    benchmark_prices = pd.DataFrame(benchmark_series).sort_index() if benchmark_series else pd.DataFrame(index=asset_prices.index)
    sector_map = _load_sector_map(root)

    return DataBundle(
        asset_prices=asset_prices.sort_index(),
        benchmark_prices=benchmark_prices,
        sector_map=sector_map,
        discovered_files=discovered,
    )
