from __future__ import annotations

from typing import Dict, List, Tuple
import math

import numpy as np

from qubo import qubo_energy

try:
    import neal
except Exception:
    neal = None


def _repair_solution(
    x: np.ndarray,
    Q: np.ndarray,
    assets: List[str],
    sector_map: Dict[str, str],
    K: int,
    max_per_sector: int,
) -> np.ndarray:
    x = x.astype(int).copy()
    n = len(x)

    def score(idx: int) -> float:
        # Approximate marginal impact for local repair.
        return float(Q[idx, idx] + 2.0 * np.dot(Q[idx, :], x) - 2.0 * Q[idx, idx] * x[idx])

    while x.sum() > K:
        ones = np.where(x == 1)[0]
        drop = max(ones, key=score)
        x[drop] = 0

    while x.sum() < K:
        zeros = np.where(x == 0)[0]
        add = min(zeros, key=score)
        x[add] = 1

    if max_per_sector > 0:
        for _ in range(n * 2):
            changed = False
            sector_counts: Dict[str, int] = {}
            for i, v in enumerate(x):
                if v == 1:
                    s = sector_map.get(assets[i], "UNKNOWN")
                    sector_counts[s] = sector_counts.get(s, 0) + 1

            over_sectors = [s for s, c in sector_counts.items() if c > max_per_sector]
            if not over_sectors:
                break

            for s in over_sectors:
                ones = [i for i in np.where(x == 1)[0] if sector_map.get(assets[i], "UNKNOWN") == s]
                if not ones:
                    continue
                drop = max(ones, key=score)
                x[drop] = 0

                zeros = [i for i in np.where(x == 0)[0] if sector_map.get(assets[i], "UNKNOWN") != s]
                if not zeros:
                    zeros = list(np.where(x == 0)[0])
                add = min(zeros, key=score)
                x[add] = 1
                changed = True

            if not changed:
                break

    return x


def _neal_anneal(Q: np.ndarray, num_reads: int = 256) -> np.ndarray:
    n = Q.shape[0]
    qdict = {}
    for i in range(n):
        for j in range(i, n):
            if Q[i, j] != 0.0:
                qdict[(i, j)] = float(Q[i, j])

    sampler = neal.SimulatedAnnealingSampler()
    sampleset = sampler.sample_qubo(qdict, num_reads=num_reads)
    best = sampleset.first.sample
    x = np.array([best[i] for i in range(n)], dtype=int)
    return x


def _custom_anneal(Q: np.ndarray, K: int, steps: int = 6000) -> np.ndarray:
    n = Q.shape[0]

    x = np.zeros(n, dtype=int)
    idx = np.random.choice(np.arange(n), size=min(K, n), replace=False)
    x[idx] = 1

    best = x.copy()
    best_e = qubo_energy(best, Q)

    t0 = 2.0
    t1 = 0.005

    for step in range(steps):
        t = t0 * ((t1 / t0) ** (step / max(steps - 1, 1)))

        ones = np.where(x == 1)[0]
        zeros = np.where(x == 0)[0]
        if len(ones) == 0 or len(zeros) == 0:
            break

        i = np.random.choice(ones)
        j = np.random.choice(zeros)

        x_new = x.copy()
        x_new[i] = 0
        x_new[j] = 1

        e_cur = qubo_energy(x, Q)
        e_new = qubo_energy(x_new, Q)
        dE = e_new - e_cur

        if dE <= 0 or np.random.rand() < math.exp(-dE / max(t, 1e-9)):
            x = x_new
            if e_new < best_e:
                best = x_new.copy()
                best_e = e_new

    return best


def select_assets_via_annealing(
    Q: np.ndarray,
    assets: List[str],
    sector_map: Dict[str, str],
    K: int,
    max_per_sector: int = 4,
    num_reads: int = 512,
) -> Tuple[List[str], np.ndarray]:
    if neal is not None:
        x = _neal_anneal(Q=Q, num_reads=num_reads)
    else:
        x = _custom_anneal(Q=Q, K=K)

    x = _repair_solution(x, Q, assets, sector_map, K, max_per_sector)

    selected_idx = np.where(x == 1)[0]
    selected_assets = [assets[i] for i in selected_idx]
    return selected_assets, x
