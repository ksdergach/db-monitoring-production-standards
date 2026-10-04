from __future__ import annotations

from datetime import UTC, datetime, timedelta

import numpy as np

SEED = 42
START_TS = datetime(2026, 1, 5, 0, 0, 0, tzinfo=UTC)
STEP = timedelta(minutes=15)
NULL_RATE = 0.02
N_POINTS = 800


def _base_values() -> tuple[np.ndarray, np.ndarray]:
    """Return the deterministic D1 row_count and null_rate arrays."""
    rng = np.random.RandomState(SEED)
    indices = np.arange(N_POINTS, dtype=float)
    row_count = 1000.0 + 10.0 * indices + rng.normal(0.0, 5.0, size=N_POINTS)
    null_rate = np.full(N_POINTS, NULL_RATE, dtype=float)
    return row_count, null_rate


def _metric_rows(values: np.ndarray) -> list[dict[str, object]]:
    """Convert numeric values to the shape returned by get_metrics()."""
    return [
        {
            "ts": (START_TS + i * STEP).isoformat(),
            "value": float(value),
            "tags": None,
        }
        for i, value in enumerate(values)
    ]


def _dataset(row_count: np.ndarray, null_rate: np.ndarray) -> dict[str, list[dict[str, object]]]:
    return {
        "row_count": _metric_rows(row_count),
        "null_rate": _metric_rows(null_rate),
    }


def d1() -> dict[str, list[dict[str, object]]]:
    """Stable growth: 800 points with row_count = 1000 + 10*i + N(0, 5)."""
    row_count, null_rate = _base_values()
    return _dataset(row_count, null_rate)


def d2() -> dict[str, list[dict[str, object]]]:
    """D1 with a spike at points 600–609."""
    row_count, null_rate = _base_values()
    row_count = row_count.copy()
    null_rate = null_rate.copy()
    row_count[600:610] *= 3.0
    null_rate[600:610] = 0.5
    return _dataset(row_count, null_rate)


def d3() -> dict[str, list[dict[str, object]]]:
    """D1 with a +5000 level shift starting at point 500."""
    row_count, null_rate = _base_values()
    row_count = row_count.copy()
    row_count[500:] += 5000.0
    return _dataset(row_count, null_rate)


def d4() -> dict[str, list[dict[str, object]]]:
    """Short series: the first five points of D1."""
    row_count, null_rate = _base_values()
    return _dataset(row_count[:5], null_rate[:5])


DATASETS = {
    "D1": d1,
    "D2": d2,
    "D3": d3,
    "D4": d4,
}
