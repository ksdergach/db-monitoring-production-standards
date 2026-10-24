"""Приёмка #54: сбор → настоящие ML/SQLite → необязательная доставка.

Подменены внешний источник метрик и отправка; ML, артефакты, UPSERT,
проектные настройки, фильтр, throttle, аудит и расчёт дрейфа — настоящие.
В сценариях отказов подменяется только явно указанный этап.
"""

from datetime import UTC, datetime, timedelta
from random import Random
from types import SimpleNamespace
from unittest.mock import MagicMock

import joblib
import pytest
from cryptography.fernet import Fernet
from sqlalchemy import create_engine, text

from app import crypto
from app import metrics_storage as storage
from app.notifications import telegram
from collectors import per_project as pp
from ml import anomaly_detector as ad
from ml import common

TOKEN = "0000000001:" + "A" * 35


def metrics(table, ts, value=10000):
    return [
        {"table_name": table, "ts": ts, "metric_name": "row_count", "value": value},
        {"table_name": table, "ts": ts, "metric_name": "null_rate", "value": 0.8},
    ]


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("FERNET_KEY", Fernet.generate_key().decode())
    crypto.reset_for_tests()
    monkeypatch.setattr(storage.settings, "MONITOR_DB_URL", f"sqlite:///{tmp_path / 'monitor.db'}")
    monkeypatch.setattr(storage, "_engine", None)
    monkeypatch.setattr(storage, "_initialized", False)
    monkeypatch.setattr(common, "MODELS_DIR", tmp_path / "models")
    source = SimpleNamespace(
        tables=["orders"], ts=datetime.now(UTC).replace(microsecond=0), value=10000
    )
    adapter = MagicMock()
    adapter.list_tables.side_effect = lambda ns: [
        {"table_name": t, "schema": ns} for t in source.tables
    ]
    monkeypatch.setattr(pp, "_build_engine", lambda *a: create_engine("sqlite:///:memory:"))
    monkeypatch.setattr(pp, "make_adapter_for_url", lambda *a, **kw: adapter)
    collect = MagicMock(side_effect=lambda table, **kw: metrics(table, source.ts, source.value))
    monkeypatch.setattr(pp.MetricsCollector, "collect", collect)
    monkeypatch.setattr("collectors.schema_collector.collect_table_schema", lambda *a, **kw: None)
    monkeypatch.setattr(telegram, "is_enabled", lambda flag: False)
    send = MagicMock(return_value=(True, None))
    monkeypatch.setattr(telegram, "send_message", send)
    drift = MagicMock(wraps=pp._refresh_drift_cache)
    monkeypatch.setattr(pp, "_refresh_drift_cache", drift)
    source.adapter, source.collect, source.send, source.drift = adapter, collect, send, drift
    yield source
    storage.get_engine().dispose()
    crypto.reset_for_tests()


def project(name):
    storage.create_user(user_id=name, email=f"{name}@example.test", password_hash="test")
    storage.create_project(project_id=name, user_id=name, name=name, slug=name)
    storage.create_connection(
        connection_id=name,
        project_id=name,
        name="source",
        dsn_encrypted=crypto.encrypt_dsn("postgresql://test:test@example.invalid/test"),
        schema_name="public",
        interval_minutes=15,
        is_active=True,
    )
    return name


def history(env, pid, table="orders", n=201, base=1000):
    rows = []
    rng = Random(base)
    for i in range(n):
        ts = env.ts - timedelta(hours=n - i)
        rows.extend(metrics(table, ts, base + rng.gauss(0, 10)))
        rows[-1]["value"] = 0.02 + rng.gauss(0, 0.001)
    storage.save_metrics(rows, pid)


def configure(pid, token=TOKEN, chat="test-chat"):
    storage.save_project_notifications(
        pid,
        telegram_bot_token=crypto.encrypt_token(token) if token else None,
        telegram_chat_id=chat,
        throttle_minutes=30,
    )


def scores(pid, table="orders"):
    return storage.get_anomaly_scores(table, pid, window=timedelta(days=1))


def assert_saved(pid):
    result = scores(pid)
    assert result
    # Реальное чтение SQL, включая нормальные точки и аномалии.
    with storage.get_engine().connect() as conn:
        count = conn.execute(
            text("SELECT count(*) FROM anomaly_scores WHERE project_id=:p"), {"p": pid}
        ).scalar_one()
    assert count == len(result)
    return result


@pytest.mark.parametrize("config", ["absent", "no-token", "no-chat", "empty", "invalid"])
def test_collect_persists_real_scores_without_usable_telegram(env, config):
    pid = project("a")
    history(env, pid)
    ad.train("orders", project_id=pid)
    if config != "absent":
        configure(
            pid,
            token=None if config in {"no-token", "empty"} else TOKEN,
            chat=None if config in {"no-chat", "empty"} else "test-chat",
        )
    if config == "invalid":
        storage.save_project_notifications(
            pid, telegram_bot_token=b"invalid-ciphertext", telegram_chat_id="test-chat"
        )
    pp.collect_for_connection(pid, pid)
    result = assert_saved(pid)
    assert result[-1]["is_anomaly"] == 1  # Дошли до этапа уведомления.
    assert storage.get_metrics("orders", "row_count", pid)[-1]["value"] == env.value
    env.send.assert_not_called()
    env.drift.assert_called_once_with(pid, ["orders"])


def test_first_training_without_telegram_uses_full_history(env):
    pid = project("a")
    history(env, pid, n=200)  # Со свежим замером ровно 201 → 200 строк признаков.
    path = common.model_path("anomaly", "orders", pid)
    assert not path.exists()
    pp.collect_for_connection(pid, pid)
    assert_saved(pid)
    payload = joblib.load(path)
    assert payload["n_points"] == 200
    assert payload["model"].n_estimators == 100
    assert payload["model"].contamination == 0.01
    assert payload["scaler"].n_features_in_ == 4
    env.send.assert_not_called()


@pytest.mark.parametrize("n", [1, 199])
def test_insufficient_training_history_is_not_a_run_failure(env, n):
    pid = project("a")
    history(env, pid, n=n)
    configure(pid)
    pp.collect_for_connection(pid, pid)
    assert scores(pid) == []
    assert not common.model_path("anomaly", "orders", pid).exists()
    env.send.assert_not_called()
    env.drift.assert_called_once()


def test_ready_model_can_score_two_ticks_without_training_minimum(env):
    pid = project("a")
    history(env, pid)
    ad.train("orders", project_id=pid)
    with storage.get_engine().begin() as conn:
        conn.execute(text("DELETE FROM metrics WHERE project_id=:p"), {"p": pid})
    history(env, pid, n=1)
    pp.collect_for_connection(pid, pid)
    assert len(assert_saved(pid)) == 1


def test_notification_uses_project_config_after_persistence_and_is_throttled(env):
    pid = project("a")
    history(env, pid)
    ad.train("orders", project_id=pid)
    configure(pid)

    def send(message, **kwargs):
        result = assert_saved(pid)  # Сохранено ещё до доставки.
        latest = max((s for s in result if s["is_anomaly"]), key=lambda s: s["ts"])
        assert f"Score: {latest['score']:.4f}" in message
        assert "Проект: a (a)" in message
        assert "Таблица: orders" in message
        assert kwargs == {"bot_token": TOKEN, "chat_id": "test-chat"}
        return True, None

    env.send.side_effect = send
    pp.collect_for_connection(pid, pid)
    first = assert_saved(pid)
    pp.collect_for_connection(pid, pid)
    assert scores(pid) == first  # Повтор окна использует UPSERT.
    env.send.assert_called_once()
    attempts = storage.get_notifications(project_id=pid)
    assert len(attempts) == 1
    assert attempts[0]["status"] == "sent"
    assert attempts[0]["chat_id"] == "test-chat"


@pytest.mark.parametrize("outcome", ["normal", "weak-score", "small-delta", "latest-filtered"])
def test_notification_selection_never_filters_saved_scores(env, monkeypatch, outcome):
    pid = project("a")
    history(env, pid)
    configure(pid)
    env.value = 1000
    result = [{"ts": env.ts.isoformat(), "score": -0.3, "is_anomaly": 1}]
    if outcome == "normal":
        result[0].update(score=0.1, is_anomaly=0)
    elif outcome in {"weak-score", "latest-filtered"}:
        result[0]["score"] = -0.003
    if outcome == "latest-filtered":
        result.append(
            {"ts": (env.ts - timedelta(minutes=1)).isoformat(), "score": -0.4, "is_anomaly": 1}
        )
    monkeypatch.setattr(ad, "score_table", lambda *a, **kw: result)
    config_loader = MagicMock(side_effect=AssertionError("Telegram прочитан до отбора"))
    monkeypatch.setattr(pp, "_load_telegram_config", config_loader)
    pp.collect_for_connection(pid, pid)
    assert len(assert_saved(pid)) == len(result)
    config_loader.assert_not_called()
    env.send.assert_not_called()


def test_two_projects_train_and_score_their_own_history(env):
    a, b = project("a"), project("b")
    history(env, a, base=1000)
    history(env, b, base=5000)
    # Разные обучающие данные проверяются через сохранённые scaler.
    ad.train("orders", project_id=a)
    ad.train("orders", project_id=b)
    configure(b)
    pp.collect_for_connection(a, a)
    pp.collect_for_connection(b, b)
    sa, sb = assert_saved(a), assert_saved(b)
    assert [s["ts"] for s in sa] == [s["ts"] for s in sb]
    assert sa != sb
    pa = joblib.load(common.model_path("anomaly", "orders", a))
    pb = joblib.load(common.model_path("anomaly", "orders", b))
    assert pb["scaler"].mean_[0] - pa["scaler"].mean_[0] == pytest.approx(4000, abs=5)
    env.send.assert_called_once()
    assert env.send.call_args.kwargs == {"bot_token": TOKEN, "chat_id": "test-chat"}
    assert storage.get_notifications(project_id=a) == []
    assert len(storage.get_notifications(project_id=b)) == 1
    before = scores(b)
    pp.collect_for_connection(a, a)
    assert scores(b) == before


@pytest.mark.parametrize("failure", ["score", "history", "save", "config", "decrypt", "notify"])
def test_table_failures_do_not_block_next_table_or_real_drift(env, monkeypatch, caplog, failure):
    pid = project("a")
    env.tables = ["a", "b"]
    configure(pid)
    for table in env.tables:
        history(env, pid, table)
        ad.train(table, project_id=pid)
    if failure in {"score", "history"}:
        original = ad.score_table

        def score(table, **kw):
            if table == "a":
                if failure == "history":
                    raise ad.InsufficientDataError("too short")
                raise RuntimeError("score failed")
            return original(table, **kw)

        monkeypatch.setattr(ad, "score_table", score)
    elif failure == "save":
        original = storage.save_anomaly_scores

        def save(rows, project_id):
            if rows[0]["table_name"] == "a":
                raise RuntimeError("save failed")
            return original(rows, project_id)

        monkeypatch.setattr(storage, "save_anomaly_scores", save)
    elif failure in {"config", "decrypt"}:
        target = storage if failure == "config" else crypto
        attr = "get_project_notifications" if failure == "config" else "decrypt_token"
        original = getattr(target, attr)
        calls = 0

        def load(*a, **kw):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise RuntimeError(f"token={TOKEN}")
            return original(*a, **kw)

        monkeypatch.setattr(target, attr, load)
    else:
        env.send.side_effect = [RuntimeError(f"token={TOKEN}"), (True, None)]
    storage.save_metrics(
        [
            {
                "table_name": "b",
                "ts": ts,
                "metric_name": "column_distribution",
                "value": 100,
                "tags": {"column": "source", "data_type": "varchar", "buckets": buckets},
            }
            for ts, buckets in [
                (
                    env.ts - timedelta(days=5),
                    [{"value": "x", "count": 90}, {"value": "y", "count": 10}],
                ),
                (env.ts, [{"value": "x", "count": 10}, {"value": "y", "count": 90}]),
            ]
        ],
        pid,
    )
    pp.collect_for_connection(pid, pid)
    assert storage.get_drift_report("b", pid)[0]["is_drift"] is True
    assert scores(pid, "b")
    if failure in {"config", "decrypt", "notify"}:
        assert scores(pid, "a")
        assert storage.get_notifications(project_id=pid, table_name="b")[0]["status"] == "sent"
    else:
        assert scores(pid, "a") == []
    env.drift.assert_called_once_with(pid, ["a", "b"])
    if failure != "history":
        assert "failed" in caplog.text or "skipped" in caplog.text
    assert TOKEN not in caplog.text


def test_failed_delivery_is_audited_and_does_not_erase_scores(env):
    pid = project("a")
    history(env, pid)
    ad.train("orders", project_id=pid)
    configure(pid)
    env.send.return_value = (False, "test delivery failure")
    pp.collect_for_connection(pid, pid)
    assert_saved(pid)
    assert storage.get_notifications(project_id=pid)[0]["status"] == "failed"
    env.drift.assert_called_once()


def test_unexpected_anomaly_stage_exception_still_runs_drift(env, monkeypatch, caplog):
    pid = project("a")
    monkeypatch.setattr(pp, "_maybe_notify_anomalies", MagicMock(side_effect=RuntimeError("stage")))
    pp.collect_for_connection(pid, pid)
    env.drift.assert_called_once_with(pid, ["orders"])
    assert "anomaly processing failed" in caplog.text


@pytest.mark.parametrize("mode", ["failed", "empty", "partial", "failed-after-save"])
def test_collection_status_preserves_postprocessing_conditions(env, monkeypatch, mode):
    pid = project("a")
    env.tables = ["a", "b"]
    stage = MagicMock()
    monkeypatch.setattr(pp, "_maybe_notify_anomalies", stage)
    if mode == "failed":
        env.adapter.list_tables.side_effect = RuntimeError("source unavailable")
    elif mode == "empty":
        env.collect.side_effect = lambda *a, **kw: []
    elif mode == "partial":
        env.collect.side_effect = [RuntimeError("table failed"), metrics("b", env.ts)]
    else:
        monkeypatch.setattr(pp, "save_run_table", MagicMock(side_effect=RuntimeError("run log")))
    pp.collect_for_connection(pid, pid)
    with storage.get_engine().connect() as conn:
        status = conn.execute(
            text("SELECT status FROM collector_runs WHERE project_id=:p"), {"p": pid}
        ).scalar_one()
        count = conn.execute(
            text("SELECT count(*) FROM metrics WHERE project_id=:p"), {"p": pid}
        ).scalar_one()
    assert (
        status
        == {
            "failed": "failed",
            "empty": "success",
            "partial": "warning",
            "failed-after-save": "failed",
        }[mode]
    )
    if mode == "partial":
        assert count == 2
        stage.assert_called_once_with(pid, ["a", "b"])
        env.drift.assert_called_once()
    else:
        assert (count > 0) == (mode == "failed-after-save")
        stage.assert_not_called()
        env.drift.assert_not_called()
