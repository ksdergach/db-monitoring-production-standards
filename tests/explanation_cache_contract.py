"""Общие проверки Issue #55 на настоящих SQLite и PostgreSQL/TimescaleDB."""

from datetime import UTC, datetime, timedelta, timezone
from unittest.mock import Mock

import pytest
from sqlalchemy import event, inspect, text

TS = "2026-04-20T12:00:00+00:00"
REQUEST = {"table": "orders", "metric": "row_count", "ts": TS}


def save(storage, project, explanation=None):
    storage.save_explanation("orders", "row_count", TS, explanation or project, "fix", 0.8, project)


def read(storage, project):
    return storage.get_cached_explanation("orders", "row_count", TS, project)


def old_cache(engine, *, populated=True):
    """Схема до Issue #55; прочие таблицы остаются на месте."""
    postgres = engine.dialect.name == "postgresql"
    timestamp = "TIMESTAMPTZ" if postgres else "TEXT"
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE llm_explanations"))
        conn.execute(
            text(f"""
            CREATE TABLE llm_explanations (
                table_name TEXT NOT NULL, metric TEXT NOT NULL, ts {timestamp} NOT NULL,
                explanation TEXT NOT NULL, suggested_fix TEXT NOT NULL,
                confidence REAL NOT NULL, created_at {timestamp} NOT NULL,
                PRIMARY KEY (table_name, metric, ts)
            )
        """)
        )
        if populated:
            conn.execute(
                text("""
                INSERT INTO llm_explanations VALUES
                    ('orders', 'row_count', :ts, 'unknown owner', 'fix', 0.8, :ts)
            """),
                {"ts": TS},
            )


def api_client(storage):
    from app.app import create_app

    storage.create_user("owner", "owner@example.com", "unused-test-hash")
    storage.create_user("other", "other@example.com", "unused-test-hash")
    for project, owner in (("A", "owner"), ("B", "owner"), ("foreign", "other")):
        storage.create_project(project, owner, project, project.lower())
    app = create_app({"TESTING": True, "LOGIN_DISABLED": False})
    client = app.test_client()
    with client.session_transaction() as session:
        session["_user_id"] = "owner"
        session["_fresh"] = True
        session["current_project_id"] = "A"
    return client


def seed_table(storage, project):
    storage.save_metrics(
        [
            {
                "ts": datetime.now(UTC),
                "table_name": "orders",
                "metric_name": "row_count",
                "value": 42,
            }
        ],
        project,
    )


class ExplanationCacheContract:
    def test_llm_schema_context_is_project_scoped(self, storage):
        from app.llm import _build_prompt

        for project in ("A", "B"):
            storage.save_schema_snapshot(
                "orders", [{"name": f"private_{project}", "type": "TEXT"}], project_id=project
            )
        prompt = _build_prompt("orders", "row_count", TS, project_id="A")
        assert "private_A" in prompt
        assert "private_B" not in prompt

    def test_new_schema_and_isolated_upsert(self, storage):
        engine = storage.get_engine()
        assert inspect(engine).get_pk_constraint("llm_explanations")["constrained_columns"] == [
            "project_id",
            "table_name",
            "metric",
            "ts",
        ]
        project_col = next(
            c for c in inspect(engine).get_columns("llm_explanations") if c["name"] == "project_id"
        )
        assert not project_col["nullable"]
        assert project_col["default"] is None
        save(storage, "A")
        save(storage, "B")
        save(storage, "A", "updated A")
        assert read(storage, "A")["explanation"] == "updated A"
        assert read(storage, "B")["explanation"] == "B"
        assert read(storage, "missing") is None
        with engine.connect() as conn:
            assert conn.execute(
                text("SELECT project_id, explanation FROM llm_explanations ORDER BY project_id")
            ).all() == [("A", "updated A"), ("B", "B")]

    @pytest.mark.parametrize("project", [None, "", " "])
    def test_project_required(self, storage, project):
        with pytest.raises(ValueError, match="project_id"):
            read(storage, project)
        with pytest.raises(ValueError, match="project_id"):
            save(storage, project)
        with pytest.raises(TypeError):
            storage.get_cached_explanation("orders", "row_count", TS)
        with pytest.raises(TypeError):
            storage.save_explanation("orders", "row_count", TS, "reason", "fix", 0.5)

    @pytest.mark.parametrize("hours", [23, 25])
    @pytest.mark.parametrize("tz", [None, UTC, timezone(timedelta(hours=5, minutes=30))])
    def test_ttl_and_timezones(self, storage, hours, tz):
        save(storage, "A")
        save(storage, "B")
        created = datetime.now(UTC) - timedelta(hours=hours)
        created = (
            created.astimezone(tz).isoformat() if tz else created.replace(tzinfo=None).isoformat()
        )
        with storage.get_engine().begin() as conn:
            if storage._is_postgres():
                conn.execute(text("SET LOCAL TIME ZONE 'UTC'"))
            conn.execute(
                text("UPDATE llm_explanations SET created_at = :created WHERE project_id = 'A'"),
                {"created": created},
            )
        assert (read(storage, "A") is not None) == (hours < 24)
        if hours > 24:
            save(storage, "A", "renewed")
            assert read(storage, "A")["explanation"] == "renewed"
        assert read(storage, "B")["explanation"] == "B"

    @pytest.mark.parametrize("populated", [False, True])
    def test_old_schema_migration_is_idempotent(self, storage, populated):
        seed_table(storage, "A")
        engine = storage.get_engine()
        old_cache(engine, populated=populated)
        storage._apply_schema(engine)
        assert read(storage, "legacy") is None
        assert read(storage, "A") is None
        save(storage, "A")
        save(storage, "B")
        storage._apply_schema(engine)
        assert read(storage, "A")["explanation"] == "A"
        assert read(storage, "B")["explanation"] == "B"
        assert storage.get_latest_metric("orders", "row_count", "A")["value"] == 42
        with engine.connect() as conn:
            assert conn.execute(text("SELECT COUNT(*) FROM llm_explanations")).scalar() == 2

    def test_migration_failure_rolls_back_ddl_and_data(self, storage):
        engine = storage.get_engine()
        old_cache(engine)

        def fail(_conn, _cursor, statement, _parameters, _context, _executemany):
            if statement.startswith(
                (
                    "ALTER TABLE llm_explanations__new RENAME",
                    "ALTER TABLE llm_explanations ADD PRIMARY KEY",
                )
            ):
                raise RuntimeError("injected migration failure")

        event.listen(engine, "before_cursor_execute", fail)
        try:
            with pytest.raises(RuntimeError, match="injected migration failure"):
                storage._apply_schema(engine)
        finally:
            event.remove(engine, "before_cursor_execute", fail)
        assert "project_id" not in {
            c["name"] for c in inspect(engine).get_columns("llm_explanations")
        }
        assert not inspect(engine).has_table("llm_explanations__new")
        with engine.connect() as conn:
            assert (
                conn.execute(text("SELECT explanation FROM llm_explanations")).scalar()
                == "unknown owner"
            )
        storage._apply_schema(engine)
        save(storage, "A")
        assert read(storage, "A")["explanation"] == "A"

    def test_api_project_switch_cache_and_expiry(self, storage, monkeypatch):
        client = api_client(storage)
        for project in ("A", "B"):
            seed_table(storage, project)
        llm = Mock(
            side_effect=lambda *args, project_id: {
                "explanation": project_id,
                "suggested_fix": "fix",
                "confidence": 0.8,
            }
        )
        monkeypatch.setattr("app.llm.explain_anomaly", llm)
        for project in ("A", "B", "A", "B"):
            assert client.post(f"/projects/{project.lower()}/switch").status_code == 302
            response = client.post("/api/explain", json=REQUEST)
            assert response.status_code == 200
            assert response.get_json() == {
                "explanation": project,
                "suggested_fix": "fix",
                "confidence": 0.8,
            }
        assert llm.call_count == 2
        with storage.get_engine().begin() as conn:
            conn.execute(
                text("UPDATE llm_explanations SET created_at = :old WHERE project_id = 'A'"),
                {"old": (datetime.now(UTC) - timedelta(hours=25)).isoformat()},
            )
        client.post("/projects/a/switch")
        assert client.post("/api/explain", json=REQUEST).get_json()["explanation"] == "A"
        assert llm.call_count == 3
        assert read(storage, "B")["explanation"] == "B"

    @pytest.mark.parametrize("cached_project", ["A", "B"])
    def test_denied_table_never_reads_cache_or_calls_llm(
        self, storage, monkeypatch, cached_project
    ):
        client = api_client(storage)
        seed_table(storage, "B")
        save(storage, cached_project)
        llm = Mock()
        monkeypatch.setattr("app.llm.explain_anomaly", llm)
        statements = []

        def record(_conn, _cursor, statement, _parameters, _context, _executemany):
            statements.append(statement)

        engine = storage.get_engine()
        event.listen(engine, "before_cursor_execute", record)
        try:
            response = client.post("/api/explain?project_id=B", json={**REQUEST, "project_id": "B"})
        finally:
            event.remove(engine, "before_cursor_execute", record)
        assert response.status_code == 404
        assert response.get_json() == {"error": "table not found"}
        assert not any("llm_explanations" in s for s in statements)
        llm.assert_not_called()

    def test_client_project_cannot_override_membership_or_server_context(
        self, storage, monkeypatch
    ):
        client = api_client(storage)
        seed_table(storage, "A")
        save(storage, "A")
        save(storage, "foreign")
        llm = Mock()
        monkeypatch.setattr("app.llm.explain_anomaly", llm)
        assert client.post("/projects/foreign/switch").status_code == 404
        # Даже устаревший session project проходит штатную серверную проверку членства.
        with client.session_transaction() as session:
            session["current_project_id"] = "foreign"
        response = client.post(
            "/api/explain?project_id=foreign", json={**REQUEST, "project_id": "foreign"}
        )
        assert response.status_code == 200
        assert response.get_json()["explanation"] == "A"
        llm.assert_not_called()

    @pytest.mark.parametrize(
        "body",
        [
            ["invalid"],
            {**REQUEST, "table": 12},
            {**REQUEST, "ts": "bad"},
            {"table": "orders"},
            {**REQUEST, "metric": "invalid"},
        ],
    )
    def test_invalid_request_precedes_cache(self, storage, monkeypatch, body):
        client = api_client(storage)
        cache = Mock(side_effect=AssertionError("cache must not be read"))
        llm = Mock(side_effect=AssertionError("LLM must not be called"))
        monkeypatch.setattr("app.api.get_cached_explanation", cache)
        monkeypatch.setattr("app.llm.explain_anomaly", llm)
        assert client.post("/api/explain", json=body).status_code == 400
        cache.assert_not_called()
        llm.assert_not_called()
