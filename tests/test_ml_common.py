"""Compatibility contracts for the shared ML helpers."""

from datetime import UTC, datetime, timedelta, timezone

import joblib
import pytest

from ml import anomaly_detector, common, forecast
from scripts import reset_db


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("2026-01-05T00:00:00Z", "2026-01-05T00:00:00+00:00"),
        ("2026-01-05T00:00:00", "2026-01-05T00:00:00+00:00"),
        ("2026-01-05T03:00:00+03:00", "2026-01-05T03:00:00+03:00"),
        (datetime(2026, 1, 5), "2026-01-05T00:00:00+00:00"),
    ],
)
def test_parse_ts_preserves_timezone_semantics(value, expected):
    assert common.parse_ts(value).isoformat() == expected


def test_parse_ts_returns_aware_datetime_unchanged():
    value = datetime(2026, 1, 5, tzinfo=timezone(timedelta(hours=3)))
    assert common.parse_ts(value) is value


@pytest.mark.parametrize(
    ("kind", "table", "project", "metric", "filename"),
    [
        ("anomaly", "orders", "legacy", None, "orders__anomaly.joblib"),
        ("forecast", "orders", "legacy", "row_count", "orders__row_count.joblib"),
        ("anomaly", "orders", "tenant-a", None, "tenant-a__orders__anomaly.joblib"),
        (
            "forecast",
            "orders",
            "tenant-a",
            "row_count",
            "tenant-a__orders__row_count.joblib",
        ),
        ("anomaly", "sales/orders 2026", "legacy", None, "sales_orders_2026__anomaly.joblib"),
        (
            "forecast",
            "sales/orders 2026",
            "legacy",
            "row/count daily",
            "sales_orders 2026__row_count daily.joblib",
        ),
        (
            "anomaly",
            "заказы/2026 год",
            "tenant/a b",
            None,
            "tenant_a_b__заказы_2026_год__anomaly.joblib",
        ),
        (
            "forecast",
            "заказы/2026 год",
            "tenant/a b",
            "row/count daily",
            "tenant_a_b__заказы_2026 год__row_count daily.joblib",
        ),
    ],
)
def test_model_path_keeps_existing_filenames(
    tmp_path, monkeypatch, kind, table, project, metric, filename
):
    monkeypatch.setattr(common, "MODELS_DIR", tmp_path)
    assert common.model_path(kind, table, project, metric) == tmp_path / filename


def test_forecast_path_requires_metric():
    with pytest.raises(ValueError, match="require a metric"):
        common.model_path("forecast", "orders")


def test_existing_exception_imports_share_one_class():
    assert forecast.InsufficientDataError is anomaly_detector.InsufficientDataError
    assert forecast.InsufficientDataError is common.InsufficientDataError


def test_existing_cached_models_load_from_shared_directory(tmp_path, monkeypatch):
    # Files named using the pre-refactor conventions must remain readable.
    monkeypatch.setattr(common, "MODELS_DIR", tmp_path)
    payload = {"trained_at": datetime(2026, 1, 5, tzinfo=UTC).isoformat()}
    joblib.dump(payload, tmp_path / "tenant_a__sales_orders_2026__anomaly.joblib")
    joblib.dump(payload, tmp_path / "tenant_a__sales_orders 2026__row_count.joblib")

    assert anomaly_detector._load_model("sales/orders 2026", "tenant a") == payload
    assert forecast._load_persisted("sales/orders 2026", "row_count", "tenant a") == payload


def test_reset_uses_shared_directory_and_preserves_other_files(tmp_path, monkeypatch):
    # Patch after importing reset_db: a copied MODELS_DIR would miss this override.
    monkeypatch.setattr(common, "MODELS_DIR", tmp_path)
    (tmp_path / "orders__anomaly.joblib").touch()
    (tmp_path / "orders__row_count.joblib").touch()
    (tmp_path / "README.md").write_text("keep")

    reset_db._clear_model_cache()

    assert sorted(p.name for p in tmp_path.iterdir()) == ["README.md"]
