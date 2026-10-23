"""Issue #55: реальный PostgreSQL/TimescaleDB, миграции и перенос SQLite.

По умолчанию используется testcontainers. TEST_TIMESCALE_URL позволяет запустить
те же проверки на локальном тестовом сервере без Docker. Нужны права CREATE
DATABASE: каждый тест создаёт и удаляет отдельную БД со случайным именем.
"""

import os
import uuid

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from tests.explanation_cache_contract import (
    ExplanationCacheContract,
    old_cache,
    read,
    save,
    seed_table,
)
from tests.integration.conftest import use_metrics_db

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def postgres_url():
    if url := os.environ.get("TEST_TIMESCALE_URL"):
        yield url
    else:
        postgres = pytest.importorskip("testcontainers.postgres")
        with postgres.PostgresContainer("timescale/timescaledb:latest-pg16") as container:
            yield container.get_connection_url()


@pytest.fixture
def storage(postgres_url):
    from app import metrics_storage

    database = "issue55_" + uuid.uuid4().hex
    admin = create_engine(postgres_url, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f"CREATE DATABASE {database}"))
    url = make_url(postgres_url).set(database=database).render_as_string(hide_password=False)
    try:
        with use_metrics_db(url):
            yield metrics_storage
    finally:
        with admin.connect() as conn:
            conn.execute(text(f"DROP DATABASE {database} WITH (FORCE)"))
        admin.dispose()


class TestTimescaleExplanationCache(ExplanationCacheContract):
    @pytest.mark.parametrize("legacy", [False, True])
    @pytest.mark.parametrize("reset", [False, True])
    def test_sqlite_transfer_preserves_project_and_destination_cache(
        self, storage, tmp_path, legacy, reset
    ):
        from scripts.migrate_metrics_to_timescale import migrate

        target = storage.settings.MONITOR_DB_URL
        save(storage, "A", "destination A")
        save(storage, "B", "destination B")
        save(storage, "C", "target only")
        source = f"sqlite:///{tmp_path / 'source.db'}"
        with use_metrics_db(source):
            seed_table(storage, "A")
            if legacy:
                old_cache(storage.get_engine())
            else:
                save(storage, "A", "source A")
                save(storage, "B", "source B")
        for _ in range(2):
            counts = migrate(source, target, reset_append=reset)
            assert counts["llm_explanations"] == (0 if legacy else 2)
            assert read(storage, "A")["explanation"] == ("destination A" if legacy else "source A")
            assert read(storage, "B")["explanation"] == ("destination B" if legacy else "source B")
            assert read(storage, "C")["explanation"] == "target only"
            assert read(storage, "legacy") is None
        metrics = storage.get_metrics("orders", "row_count", "A")
        assert len(metrics) == (1 if reset else 2)
        assert all(m["value"] == 42 for m in metrics)
