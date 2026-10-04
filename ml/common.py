"""Shared timestamp, storage-path and error contracts for ML modules."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"


class InsufficientDataError(Exception):
    """Raised when there is not enough history to train or use a model."""


def parse_ts(value: str | datetime) -> datetime:
    """Parse ISO timestamps, treating timezone-naive values as UTC."""
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def model_path(
    kind: Literal["anomaly", "forecast"],
    table: str,
    project_id: str = "legacy",
    metric: str | None = None,
) -> Path:
    """Return the existing on-disk filename without migrating model files.

    Forecast filenames historically preserve spaces in table/metric names;
    anomaly filenames replace spaces with underscores. Both replace slashes.
    Legacy models have no project prefix.
    """
    if kind == "anomaly":
        safe = table.replace("/", "_").replace(" ", "_") + "__anomaly"
    elif kind == "forecast":
        if metric is None:
            raise ValueError("forecast model paths require a metric")
        safe = f"{table}__{metric}".replace("/", "_")
    else:
        raise ValueError(f"unknown model kind: {kind}")
    if project_id == "legacy":
        return MODELS_DIR / f"{safe}.joblib"
    safe_project = project_id.replace("/", "_").replace(" ", "_")
    return MODELS_DIR / f"{safe_project}__{safe}.joblib"
