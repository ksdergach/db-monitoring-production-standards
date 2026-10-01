# Базовые замеры перед практикой

Состояние проекта до начала практики. Это колонка «было» для отчёта.

- Коммит: `1a869e4bb24c2b0e238249e04ca46f97534a2a1f`, тег `practice-start`
- Дата замеров: 01.10.2026
- Окружение: macOS 26.5.2, arm64; CPython 3.12.7; Docker 29.4.1
- Зависимости установлены из `requirements.txt` и `requirements-dev.txt`. Точные версии всех 106 пакетов — в `baseline-freeze.txt`

| Метрика | Значение | Команда |
|---|---|---|
| Unit-тесты | 988 passed, 48 deselected | `venv/bin/pytest` |
| Покрытие: общее / `ml/` | 86 % / 81 % | `venv/bin/coverage run --source=app,collectors,ml -m pytest`, затем `venv/bin/coverage report --include="app/*,collectors/*"` и `venv/bin/coverage report --include="ml/*"` |
| Неотформатированные файлы | 112 из 127 | `venv/bin/ruff format --check . \| tail -1` (ruff 0.9.4) |
| Размер Docker-образа | 1,81 ГБ (столбец DISK USAGE), в сжатом виде 399 МБ (CONTENT SIZE); linux/arm64 | `docker build -t dbm:baseline . && docker image ls dbm:baseline` |
| Длительность CI | 6 мин 08 с на `1a869e4` (прогон красный); 5 мин 27 с на `ef6df6d` (зелёный) | Actions → прогон `tests` на `master` |

На коммите `1a869e4` задание `integration` завершилось с ошибкой: образ `minio/minio` удалён из Docker Hub. Это исправлено в задаче 0.1 (#24). Для сравнения «было → стало» берётся зелёный прогон. Время меняется от запуска к запуску в пределах минуты.
