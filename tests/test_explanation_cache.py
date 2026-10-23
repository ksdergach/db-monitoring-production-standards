"""Контракт кэша объяснений на SQLite."""

import pytest

from tests.explanation_cache_contract import ExplanationCacheContract
from tests.integration.conftest import use_metrics_db


@pytest.fixture
def storage(tmp_path):
    from app import metrics_storage

    with use_metrics_db(f"sqlite:///{tmp_path / 'cache.db'}"):
        yield metrics_storage


class TestSQLiteExplanationCache(ExplanationCacheContract):
    pass
