from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class MLSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ML_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ANOMALY_N_ESTIMATORS: int = 100
    ANOMALY_CONTAMINATION: float = Field(default=0.01, gt=0, le=0.5)
    ANOMALY_RANDOM_STATE: int = 42
    ANOMALY_MIN_POINTS: int = 200
    ANOMALY_TRAIN_WINDOW_DAYS: int = 60

    FORECAST_INTERVAL_WIDTH: float = Field(default=0.95, gt=0, lt=1)
    FORECAST_WEEKLY_SEASONALITY: bool = True
    FORECAST_DAILY_SEASONALITY: bool = False
    FORECAST_MIN_PROPHET_DAYS: int = 7
    FORECAST_SEVERE_DROP_RATIO: float = 0.2

    CHANGEPOINT_PELT_PENALTY: float = 6.0
    CHANGEPOINT_MIN_SCORE: float = 1.5
    CHANGEPOINT_MIN_RELATIVE_SHIFT: float = 0.15
    CHANGEPOINT_WINDOW_DAYS: int = 14

    DRIFT_PSI_WARN: float = 0.2
    DRIFT_PSI_CRITICAL: float = 0.25
    DRIFT_KS_PVALUE: float = 0.05
    DRIFT_BASELINE_DAYS: int = 7

    @model_validator(mode="after")
    def validate_psi_thresholds(self) -> "MLSettings":
        if self.DRIFT_PSI_WARN >= self.DRIFT_PSI_CRITICAL:
            raise ValueError("DRIFT_PSI_WARN must be less than DRIFT_PSI_CRITICAL")
        return self


ml_settings = MLSettings()
