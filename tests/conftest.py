import os

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")


@pytest.fixture(autouse=True)
def _ml_settings_defaults(monkeypatch):
    """Run tests with ML defaults regardless of local .env or exported ML_*."""
    from ml.settings import MLSettings, ml_settings

    for name, field in MLSettings.model_fields.items():
        monkeypatch.setattr(ml_settings, name, field.default)
