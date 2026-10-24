"""Приёмочные проверки #56: SQLite → PELT → события → проектный Telegram."""

from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import text

from app import crypto
from app import metrics_storage as ms
from app.notifications import telegram
from collectors import scheduler
from ml import changepoint


@pytest.fixture
def storage(tmp_path, monkeypatch):
    monkeypatch.setattr(ms.settings, "MONITOR_DB_URL", f"sqlite:///{tmp_path / 'metrics.db'}")
    monkeypatch.setattr(ms, "_engine", None)
    monkeypatch.setattr(ms, "_initialized", False)
    monkeypatch.setenv("FERNET_KEY", Fernet.generate_key().decode())
    crypto.reset_for_tests()
    ms.get_engine()
    for project in ["project-a", "project-b", "legacy", "no-telegram", "schema-only"]:
        user = ms.create_user(
            user_id=f"user-{project}", email=f"{project}@example.com", password_hash="x"
        )
        ms.create_project(project_id=project, user_id=user["id"], name=project, slug=project)
    yield ms
    ms.get_engine().dispose()
    crypto.reset_for_tests()


@pytest.fixture(autouse=True)
def external_services(monkeypatch):
    # Любой сетевой Telegram-вызов перехватывается, включая legacy и тесты ошибок.
    send = Mock(return_value=(True, None))
    monkeypatch.setattr(telegram, "send_message", send)
    source = Mock(return_value=[])
    monkeypatch.setattr("app.db.list_tables", source)
    return send, source


@pytest.fixture
def start():
    return datetime.now(UTC).replace(microsecond=0) - timedelta(hours=20)


def seed(storage, start, project="project-a", table="orders", metric="null_rate", values=None):
    if values is None:
        values = [0.02] * 30 + [0.20] * 30
    storage.save_metrics(
        [
            {
                "ts": start + timedelta(minutes=15 * i),
                "table_name": table,
                "metric_name": metric,
                "value": value,
            }
            for i, value in enumerate(values)
        ],
        project,
    )


def configure(storage, project="project-a", *, token="test-token-a", chat="111", throttle=30):
    storage.save_project_notifications(
        project,
        telegram_bot_token=crypto.encrypt_token(token),
        telegram_chat_id=chat,
        throttle_minutes=throttle,
    )


def events(storage, project="project-a", table="orders", metric=None):
    return storage.get_changepoints(table, metric_name=metric, project_id=project)


def expire_throttle(storage):
    with storage.get_engine().begin() as conn:
        conn.execute(text("DELETE FROM telegram_throttle"))


@pytest.mark.parametrize("metric", ["row_count", "null_rate"])
@pytest.mark.parametrize("config", ["absent", "no_token", "no_chat", "bad_ciphertext"])
def test_events_saved_without_usable_telegram(
    storage, start, monkeypatch, external_services, metric, config, caplog
):
    values = [100.0] * 30 + [1000.0] * 30 if metric == "row_count" else None
    seed(storage, start, metric=metric, values=values)
    if config != "absent":
        storage.save_project_notifications(
            "project-a",
            telegram_bot_token=(
                None
                if config == "no_token"
                else b"invalid-ciphertext"
                if config == "bad_ciphertext"
                else crypto.encrypt_token("test-token-a")
            ),
            telegram_chat_id=None if config == "no_chat" else "111",
        )

    load = telegram.load_project_telegram_config
    checked = []

    def load_after_save(project):
        if project == "project-a":
            assert events(storage), "Настройки прочитаны до записи событий"
            checked.append(project)
        return load(project)

    monkeypatch.setattr(telegram, "load_project_telegram_config", load_after_save)
    scheduler.detect_changepoints()

    saved = events(storage, metric=metric)
    assert len(saved) == 1
    assert saved[0]["value_before"] == (100.0 if metric == "row_count" else 0.02)
    assert saved[0]["value_after"] == (1000.0 if metric == "row_count" else 0.20)
    assert checked == ["project-a"]
    external_services[0].assert_not_called()
    assert storage.get_notifications(project_id="project-a") == []
    if config == "bad_ciphertext":
        assert "failed to decrypt" in caplog.text
        assert "invalid-ciphertext" not in caplog.text


def test_two_projects_same_tables_metrics_and_times(storage, start, external_services):
    for project, before, after, token, chat in [
        ("project-a", 0.02, 0.20, "test-token-a", "111"),
        ("project-b", 0.80, 0.10, "test-token-b", "222"),
    ]:
        seed(storage, start, project, values=[before] * 30 + [after] * 30)
        configure(storage, project, token=token, chat=chat)
    # Таблица только второго проекта не должна появиться у первого.
    seed(storage, start, "project-b", table="private_b")

    scheduler.detect_changepoints()

    a, b = events(storage, "project-a"), events(storage, "project-b")
    assert len(a) == len(b) == 1
    assert a[0]["ts"] == b[0]["ts"]
    assert (a[0]["value_before"], a[0]["value_after"]) == (0.02, 0.20)
    assert (b[0]["value_before"], b[0]["value_after"]) == (0.80, 0.10)
    assert events(storage, "project-a", "private_b") == []
    assert len(events(storage, "project-b", "private_b")) == 1
    calls = external_services[0].call_args_list
    assert len(calls) == 3
    assert {(c.kwargs["bot_token"], c.kwargs["chat_id"]) for c in calls} == {
        ("test-token-a", "111"),
        ("test-token-b", "222"),
    }
    for project, chat, count in [("project-a", "111", 1), ("project-b", "222", 2)]:
        audit = storage.get_notifications(project_id=project)
        assert len(audit) == count
        assert all(n["chat_id"] == chat and n["status"] == "sent" for n in audit)


def test_repeated_real_pelt_does_not_repeat_events_or_delivery(storage, start, external_services):
    seed(storage, start)
    configure(storage)
    scheduler.detect_changepoints()
    first = events(storage)
    assert len(first) == 1
    assert external_services[0].call_count == 1
    # Исключаем throttle как причину отсутствия повторной доставки.
    expire_throttle(storage)
    scheduler.detect_changepoints()
    assert events(storage) == first
    assert external_services[0].call_count == 1
    assert len(storage.get_notifications(project_id="project-a")) == 1


def test_stronger_cluster_update_and_opposite_direction(
    storage, start, monkeypatch, external_services
):
    seed(storage, start)
    configure(storage)
    event = {
        "ts": start + timedelta(hours=8),
        "table_name": "orders",
        "metric_name": "null_rate",
        "score": 5.0,
        "value_before": 0.02,
        "value_after": 0.20,
    }
    # Управляем выходом модели для точной проверки контракта 72-часового кластера.
    # detect_all, запись, чтение, throttle и аудит остаются настоящими.
    output = [event]
    monkeypatch.setattr(
        changepoint,
        "detect_changepoints",
        lambda table, metric, **kw: output
        if kw["project_id"] == "project-a" and metric == "null_rate"
        else [],
    )
    scheduler.detect_changepoints()
    output = [{**event, "ts": event["ts"] + timedelta(hours=1), "score": 9.0}]
    expire_throttle(storage)
    scheduler.detect_changepoints()
    assert len(events(storage)) == 1
    assert events(storage)[0]["score"] == 9.0
    assert external_services[0].call_count == 2
    output = [{**event, "ts": event["ts"] + timedelta(hours=2), "score": 7.0}]
    expire_throttle(storage)
    scheduler.detect_changepoints()
    assert events(storage)[0]["score"] == 9.0
    assert external_services[0].call_count == 2
    output = [
        {**event, "ts": event["ts"] + timedelta(hours=3), "value_before": 0.20, "value_after": 0.02}
    ]
    scheduler.detect_changepoints()
    saved = events(storage)
    assert len(saved) == 2
    assert {e["value_after"] > e["value_before"] for e in saved} == {True, False}
    assert external_services[0].call_count == 3


def test_active_throttle_does_not_prevent_storage(storage, start, external_services):
    seed(storage, start)
    configure(storage, throttle=60)
    storage.update_throttle("project-a", "orders", "changepoint_null_rate")
    with storage.get_engine().begin() as conn:
        conn.execute(
            text("UPDATE telegram_throttle SET last_sent_at = :ts"),
            {"ts": (datetime.now(UTC) - timedelta(minutes=45)).isoformat()},
        )
    scheduler.detect_changepoints()
    assert len(events(storage)) == 1
    external_services[0].assert_not_called()
    assert storage.get_notifications(project_id="project-a") == []


@pytest.mark.parametrize(
    "stage", ["tables", "detect_all", "read_metrics", "save", "config", "notify"]
)
def test_project_failure_does_not_block_next(
    storage, start, monkeypatch, external_services, caplog, stage
):
    for project in ["project-a", "project-b"]:
        seed(storage, start, project)
        configure(storage, project, token=f"test-token-{project}", chat=project)
    # Гарантируем порядок, не подменяя выбор проектов реальным хранилищем.
    original_ids = storage.list_project_ids_with_metrics
    monkeypatch.setattr(storage, "list_project_ids_with_metrics", lambda: sorted(original_ids()))
    target, name, pid_position = {
        "tables": (storage, "list_metric_tables", 0),
        "detect_all": (changepoint, "detect_all", None),
        "read_metrics": (changepoint, "get_metrics", 2),
        "save": (changepoint, "save_changepoints", None),
        "config": (telegram, "load_project_telegram_config", 0),
        "notify": (telegram, "notify_changepoint", 0),
    }[stage]
    original = getattr(target, name)
    secret = "123456789:" + "x" * 35

    def fail_a(*args, **kwargs):
        project = kwargs.get("project_id") if pid_position is None else args[pid_position]
        if project == "project-a":
            raise RuntimeError(
                f"failure token={secret} postgresql://reader:secret-password@db/metrics"
            )
        return original(*args, **kwargs)

    monkeypatch.setattr(target, name, fail_a)
    scheduler.detect_changepoints()

    assert len(events(storage, "project-b")) == 1
    assert storage.get_notifications(project_id="project-b")[0]["status"] == "sent"
    if stage in {"config", "notify"}:
        assert len(events(storage, "project-a")) == 1
    else:
        assert events(storage, "project-a") == []
    assert "project=project-a" in caplog.text
    assert "failure" in caplog.text
    assert secret not in caplog.text
    assert "secret-password" not in caplog.text
    assert "***" in caplog.text
    assert any(c.kwargs["chat_id"] == "project-b" for c in external_services[0].call_args_list)


@pytest.mark.parametrize("stage", ["read_metrics", "save"])
def test_failed_series_allows_next_metric_and_table(storage, start, monkeypatch, caplog, stage):
    seed(storage, start, metric="row_count", values=[100.0] * 30 + [1000.0] * 30)
    seed(storage, start)
    seed(storage, start, table="users")
    name = "get_metrics" if stage == "read_metrics" else "save_changepoints"
    original = getattr(changepoint, name)

    def fail_one(*args, **kwargs):
        table, metric = (
            (args[0], args[1])
            if stage == "read_metrics"
            else (args[0][0]["table_name"], args[0][0]["metric_name"])
        )
        if (table, metric) == ("orders", "row_count"):
            raise RuntimeError("series unavailable")
        return original(*args, **kwargs)

    monkeypatch.setattr(changepoint, name, fail_one)
    scheduler.detect_changepoints()
    assert events(storage, metric="row_count") == []
    assert len(events(storage, metric="null_rate")) == 1
    assert len(events(storage, table="users")) == 1
    assert "orders/row_count" in caplog.text


def test_network_failure_keeps_events_and_failed_attempt(
    storage, start, external_services, monkeypatch
):
    from telegram.error import NetworkError

    for project in ["project-a", "project-b"]:
        seed(storage, start, project)
        configure(storage, project, token="123456789:" + "x" * 35, chat=project)
    # Настоящий send_message обрабатывает сетевой отказ и сохраняет аудит.
    # Исходная функция сохранена до подмены внешнего сервиса фикстурой.
    monkeypatch.setattr(telegram, "send_message", REAL_SEND_MESSAGE)

    def network_error(coro):
        coro.close()
        raise NetworkError("network unavailable")

    monkeypatch.setattr(telegram.asyncio, "run", network_error)
    scheduler.detect_changepoints()
    for project in ["project-a", "project-b"]:
        assert len(events(storage, project)) == 1
        audit = storage.get_notifications(project_id=project)
        assert len(audit) == 1
        assert audit[0]["status"] == "failed"
        assert "Ошибка сети" in audit[0]["error"]
        assert not storage.is_throttled(project, "orders", "changepoint_null_rate")


REAL_SEND_MESSAGE = telegram.send_message


def test_legacy_uses_global_tables_when_metric_table_list_empty(
    storage, start, monkeypatch, external_services
):
    seed(storage, start, "legacy")
    configure(storage, "legacy", token="legacy-token", chat="legacy-chat")
    original = storage.list_metric_tables
    monkeypatch.setattr(
        storage, "list_metric_tables", lambda p: [] if p == "legacy" else original(p)
    )
    external_services[1].return_value = [{"table_name": "orders"}]
    scheduler.detect_changepoints()
    assert len(events(storage, "legacy")) == 1
    external_services[1].assert_called_once_with()
    assert external_services[0].call_args.kwargs == {
        "bot_token": "legacy-token",
        "chat_id": "legacy-chat",
    }


def test_legacy_with_metrics_is_included_once_without_global_source(
    storage, start, external_services
):
    seed(storage, start, "legacy")
    seed(storage, start, "project-a")
    configure(storage, "legacy")
    scheduler.detect_changepoints()
    assert scheduler._iter_retrain_projects().count("legacy") == 1
    assert len(events(storage, "legacy")) == len(events(storage)) == 1
    external_services[1].assert_not_called()
    assert external_services[0].call_count == 1


def test_unavailable_legacy_source_does_not_block_tenant(storage, start, external_services, caplog):
    seed(storage, start)
    external_services[1].side_effect = RuntimeError("source unavailable")
    scheduler.detect_changepoints()
    assert len(events(storage)) == 1
    assert "project=legacy" in caplog.text
    assert "source unavailable" in caplog.text


@pytest.mark.parametrize("values", [[], [0.02] * 3, [0.02] * 60])
def test_empty_short_or_stable_history_has_no_events(storage, start, external_services, values):
    seed(storage, start, values=values)
    configure(storage)
    scheduler.detect_changepoints()
    assert events(storage) == []
    external_services[0].assert_not_called()


def test_ordinary_empty_project_does_not_use_global_tables(storage, monkeypatch, external_services):
    # Метрики могли быть удалены после формирования списка проектов.
    monkeypatch.setattr(storage, "list_project_ids_with_metrics", lambda: ["project-a"])
    scheduler.detect_changepoints()
    assert events(storage) == []
    external_services[1].assert_called_once_with()  # Только legacy, не project-a.


def test_schema_notification_selection_stays_independent(storage, start, external_services):
    seed(storage, start, "no-telegram")
    configure(
        storage, "schema-only"
    )  # Нет метрик: проект всё равно пригоден для уведомлений о схеме.
    assert set(scheduler._iter_notification_projects()) == {"legacy", "schema-only"}
    assert set(scheduler._iter_retrain_projects()) == {"legacy", "no-telegram"}


def test_hourly_job_id_and_schedule_unchanged(monkeypatch):
    fake = Mock(running=False)
    monkeypatch.setattr(scheduler, "_scheduler", None)
    monkeypatch.setattr(scheduler, "BackgroundScheduler", Mock(return_value=fake))
    monkeypatch.setattr(scheduler.atexit, "register", Mock())
    monkeypatch.setattr("collectors.per_project.register_jobs_for_all_active_connections", Mock())
    scheduler.start_scheduler(Mock(config={}))
    cp = [c for c in fake.add_job.call_args_list if c.args[0] is scheduler.detect_changepoints]
    assert len(cp) == 1
    assert cp[0].args[1] == "interval"
    assert cp[0].kwargs == {"hours": 1, "id": "detect_changepoints", "name": "detect_changepoints"}


def test_notification_failure_allows_next_event(storage, start, monkeypatch, caplog):
    seed(storage, start)
    seed(storage, start, table="users")
    configure(storage)
    original = telegram.notify_changepoint

    def fail_orders(project, table, *args, **kwargs):
        if table == "orders":
            raise RuntimeError("delivery unavailable")
        return original(project, table, *args, **kwargs)

    monkeypatch.setattr(telegram, "notify_changepoint", fail_orders)
    scheduler.detect_changepoints()
    assert len(events(storage)) == len(events(storage, table="users")) == 1
    audit = storage.get_notifications(project_id="project-a")
    assert len(audit) == 1
    assert audit[0]["table_name"] == "users" and audit[0]["status"] == "sent"
    assert "delivery unavailable" in caplog.text


def test_stronger_event_saved_while_delivery_throttled(storage, start, external_services):
    seed(storage, start)
    configure(storage)
    scheduler.detect_changepoints()
    first = events(storage)[0]
    # Метрики append-only: заменяем тестовую историю, сохраняя события и throttle.
    with storage.get_engine().begin() as conn:
        conn.execute(text("DELETE FROM metrics WHERE project_id = 'project-a'"))
    seed(storage, start, values=[0.02] * 30 + [0.80] * 30)
    scheduler.detect_changepoints()
    updated = events(storage)
    assert len(updated) == 1
    assert updated[0]["score"] > first["score"]
    assert updated[0]["value_after"] == 0.80
    assert external_services[0].call_count == 1
    assert len(storage.get_notifications(project_id="project-a")) == 1


def test_saved_events_available_in_api_for_current_project(storage, start):
    from app.app import create_app

    seed(storage, start, "project-a")
    seed(storage, start, "project-b", values=[0.80] * 30 + [0.10] * 30)
    scheduler.detect_changepoints()
    app = create_app({"TESTING": True, "LOGIN_DISABLED": False, "WTF_CSRF_ENABLED": False})
    client = app.test_client()
    for project, expected in [("project-a", 0.20), ("project-b", 0.10)]:
        with client.session_transaction() as session:
            session["_user_id"] = f"user-{project}"
            session["_fresh"] = True
        response = client.get("/api/changepoints/orders?metric=null_rate")
        assert response.status_code == 200
        payload = response.get_json()
        assert len(payload) == 1
        assert payload[0]["value_after"] == expected
        assert payload == events(storage, project)
