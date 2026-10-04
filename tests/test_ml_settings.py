from pathlib import Path

import pytest
from pydantic import ValidationError

from ml.settings import MLSettings

ML_ENV_VARS = (
    "ML_ANOMALY_N_ESTIMATORS",
    "ML_ANOMALY_CONTAMINATION",
    "ML_ANOMALY_RANDOM_STATE",
    "ML_ANOMALY_MIN_POINTS",
    "ML_ANOMALY_TRAIN_WINDOW_DAYS",
    "ML_FORECAST_INTERVAL_WIDTH",
    "ML_FORECAST_WEEKLY_SEASONALITY",
    "ML_FORECAST_DAILY_SEASONALITY",
    "ML_FORECAST_MIN_PROPHET_DAYS",
    "ML_FORECAST_SEVERE_DROP_RATIO",
    "ML_CHANGEPOINT_PELT_PENALTY",
    "ML_CHANGEPOINT_MIN_SCORE",
    "ML_CHANGEPOINT_MIN_RELATIVE_SHIFT",
    "ML_CHANGEPOINT_WINDOW_DAYS",
    "ML_DRIFT_PSI_WARN",
    "ML_DRIFT_PSI_CRITICAL",
    "ML_DRIFT_KS_PVALUE",
    "ML_DRIFT_BASELINE_DAYS",
)


def test_defaults_do_not_depend_on_env_file(monkeypatch):
    for name in ML_ENV_VARS:
        monkeypatch.delenv(name, raising=False)

    settings = MLSettings(_env_file=None)

    assert settings.ANOMALY_CONTAMINATION == 0.01
    assert settings.FORECAST_INTERVAL_WIDTH == 0.95
    assert settings.CHANGEPOINT_PELT_PENALTY == 6.0
    assert settings.DRIFT_PSI_WARN == 0.2
    assert settings.DRIFT_PSI_CRITICAL == 0.25


def test_anomaly_contamination_from_environment(monkeypatch):
    monkeypatch.setenv("ML_ANOMALY_CONTAMINATION", "0.05")

    settings = MLSettings(_env_file=None)

    assert settings.ANOMALY_CONTAMINATION == 0.05


def test_anomaly_contamination_above_limit_is_invalid():
    with pytest.raises(ValidationError):
        MLSettings(_env_file=None, ANOMALY_CONTAMINATION=0.6)


@pytest.mark.parametrize("value", [0.0, 1.0])
def test_forecast_interval_width_boundaries_are_invalid(value):
    with pytest.raises(ValidationError):
        MLSettings(_env_file=None, FORECAST_INTERVAL_WIDTH=value)


def test_equal_psi_thresholds_are_invalid():
    with pytest.raises(ValidationError):
        MLSettings(
            _env_file=None,
            DRIFT_PSI_WARN=0.25,
            DRIFT_PSI_CRITICAL=0.25,
        )


def test_all_ml_variables_are_documented_in_env_example():
    env_example = (Path(__file__).resolve().parents[1] / ".env.example").read_text(encoding="utf-8")

    for name in ML_ENV_VARS:
        assert f"# {name}=" in env_example
