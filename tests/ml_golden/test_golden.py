from __future__ import annotations

import json
import os
import platform
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from ml import anomaly_detector as anomaly
from ml import changepoint, common
from ml import forecast as forecast_mod

from .datasets import d1, d2, d3, d4

TABLE = "golden_table"
PROJECT_ID = "golden-project"
EXPECTED_DIR = Path(__file__).parent / "expected"
UPDATE_GOLDEN = os.environ.get("GOLDEN_UPDATE") == "1"
PROPHET_GOLDEN_PLATFORM = (
    platform.system().lower() == "linux" and platform.machine().lower() == "x86_64"
)


def _write_expected(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _assert_close(actual: Any, expected: Any, *, rtol: float, path: str = "root") -> None:
    if isinstance(expected, dict):
        assert isinstance(actual, dict), f"{path}: expected dict, got {type(actual).__name__}"
        assert actual.keys() == expected.keys(), (
            f"{path}: keys differ: actual={list(actual.keys())}, expected={list(expected.keys())}"
        )
        for key in expected:
            _assert_close(actual[key], expected[key], rtol=rtol, path=f"{path}.{key}")
        return

    if isinstance(expected, list):
        assert isinstance(actual, list), f"{path}: expected list, got {type(actual).__name__}"
        assert len(actual) == len(expected), (
            f"{path}: list length differs: actual={len(actual)}, expected={len(expected)}"
        )
        for index, (actual_item, expected_item) in enumerate(zip(actual, expected, strict=True)):
            _assert_close(
                actual_item,
                expected_item,
                rtol=rtol,
                path=f"{path}[{index}]",
            )
        return

    is_expected_number = isinstance(expected, int | float) and not isinstance(expected, bool)
    is_actual_number = isinstance(actual, int | float) and not isinstance(actual, bool)
    if is_expected_number and is_actual_number:
        np.testing.assert_allclose(
            float(actual),
            float(expected),
            rtol=rtol,
            atol=0.0,
            err_msg=path,
        )
        return

    assert actual == expected, f"{path}: actual={actual!r}, expected={expected!r}"


def _assert_or_update(name: str, actual: Any, *, rtol: float) -> None:
    path = EXPECTED_DIR / name

    if UPDATE_GOLDEN:
        _write_expected(path, actual)
        return

    assert path.exists(), (
        f"Missing golden file: {path}. Regenerate expected results with GOLDEN_UPDATE=1."
    )
    expected = json.loads(path.read_text(encoding="utf-8"))
    _assert_close(actual, expected, rtol=rtol)


def _patch_metrics(monkeypatch, module, dataset: dict[str, list[dict[str, object]]]) -> None:
    def fake_get_metrics(
        table: str,
        metric: str,
        project_id: str = "legacy",
        **_: Any,
    ) -> list[dict[str, object]]:
        del table, project_id
        return dataset[metric]

    monkeypatch.setattr(module, "get_metrics", fake_get_metrics)


@pytest.mark.parametrize(
    ("name", "factory"),
    [
        ("d1", d1),
        ("d2", d2),
    ],
)
def test_anomaly_golden(name, factory, tmp_path, monkeypatch):
    dataset = factory()
    monkeypatch.setattr(common, "MODELS_DIR", tmp_path)
    _patch_metrics(monkeypatch, anomaly, dataset)

    metadata = anomaly.train(TABLE, project_id=PROJECT_ID)
    assert metadata["n_points"] >= anomaly.MIN_POINTS

    actual = anomaly.score_table(
        TABLE,
        window_days=14,
        project_id=PROJECT_ID,
    )
    _assert_or_update(f"anomaly_{name}.json", actual, rtol=1e-9)


def test_anomaly_d4_raises_insufficient_data(tmp_path, monkeypatch):
    dataset = d4()
    monkeypatch.setattr(common, "MODELS_DIR", tmp_path)
    _patch_metrics(monkeypatch, anomaly, dataset)

    with pytest.raises(anomaly.InsufficientDataError):
        anomaly.train(TABLE, project_id=PROJECT_ID)


@pytest.mark.parametrize(
    ("name", "factory"),
    [
        ("d1", d1),
        ("d3", d3),
    ],
)
def test_changepoint_golden(name, factory, monkeypatch):
    dataset = factory()
    _patch_metrics(monkeypatch, changepoint, dataset)

    actual = changepoint.detect_changepoints(
        TABLE,
        "row_count",
        window_days=60,
        project_id=PROJECT_ID,
    )
    _assert_or_update(f"changepoint_{name}.json", actual, rtol=1e-9)


def test_forecast_linear_golden(tmp_path, monkeypatch):
    dataset = d1()
    dataset["row_count"] = dataset["row_count"][:300]

    monkeypatch.setattr(common, "MODELS_DIR", tmp_path)
    monkeypatch.setattr(forecast_mod, "_HAS_PROPHET", False)
    monkeypatch.setattr(forecast_mod, "get_changepoints", lambda *args, **kwargs: [])
    _patch_metrics(monkeypatch, forecast_mod, dataset)

    actual = forecast_mod.forecast(
        TABLE,
        "row_count",
        horizon_days=7,
        project_id=PROJECT_ID,
    )
    _assert_or_update("forecast_linear_d1.json", actual, rtol=1e-9)


@pytest.mark.skipif(
    not PROPHET_GOLDEN_PLATFORM,
    reason=(
        "Prophet golden is validated on Linux x86_64 (CI); other platforms may differ by up to 0.2%"
    ),
)
def test_forecast_prophet_golden(tmp_path, monkeypatch):
    assert forecast_mod._HAS_PROPHET, "Prophet is required for the Prophet golden test"

    dataset = d1()
    monkeypatch.setattr(common, "MODELS_DIR", tmp_path)
    monkeypatch.setattr(forecast_mod, "get_changepoints", lambda *args, **kwargs: [])
    _patch_metrics(monkeypatch, forecast_mod, dataset)

    np.random.seed(42)
    actual = forecast_mod.forecast(
        TABLE,
        "row_count",
        horizon_days=7,
        project_id=PROJECT_ID,
    )
    _assert_or_update("forecast_prophet_d1.json", actual, rtol=1e-3)
