# Бизнес-применение МО: production-стандарты для db-monitoring

План практики по заданиям 2, 3 и 4. Репозиторий практики: `ksdergach/db-monitoring-production-standards` — независимая копия проекта `aleksandr-novikov/db-monitoring` с полной историей коммитов.
Версия от 01.10.2026. В плане 15 задач: 14 полностью покрывают три пункта задания, ещё одна (0.1) возвращает зелёный CI на `master`. Результат каждой можно показать. Всё остальное вынесено в раздел «Бэклог» в конце.

## Как план покрывает задание

| Пункт задания | Задачи | Результат |
|---|---|---|
| 3. Настройка pre-commit, Poetry, линтеров | 3.1–3.6 | зависимости описаны в `pyproject.toml` и `poetry.lock`; ruff (проверка и форматирование) и mypy запускаются перед каждым коммитом и в CI |
| 4. Интеграция виртуального окружения в Git-репозиторий ML-проекта | 4.1–4.3 | окружение описано файлами в репозитории и одной командой создаётся у разработчика, в CI и в Docker |
| 2. Рефакторинг кода ML-проекта под production-стандарты | 2.1–2.5 | в ML-коде нет дублирования; параметры моделей заданы конфигурацией и проверяются; результаты моделей защищены эталонными тестами; приложение не стартует с небезопасными секретами |

## Как устроен план
- Порядок частей: часть 0 (зелёный CI) → задание 3 → задание 4 → задание 2. Сначала инструменты контроля качества, затем окружение, затем рефакторинг под их защитой.
- **Проект не начинается с нуля.** Линтер, тесты, CI и Docker в нём уже есть, поэтому в отчёте и на показе каждый пункт описывается как «было → стало».
- **Размер:** S — до 3 ч · M — 0,5–1 день. В плане 9 задач S и 6 задач M — примерно 6–9 рабочих дней на одного человека.
- **Как сдаётся задача:** ветка от `master` → PR в `master` со ссылкой на задачу (`Closes #<номер>`) → CI зелёный → в задаче отмечены пункты «Готово, когда». Форматирование и изменения логики — в разных коммитах.
- В конце каждой части есть список «Что показываем»: из этих пунктов собирается презентация.

## Порядок работы команды

Задачи мешают друг другу там, где правят одни и те же файлы. Поэтому работа разбита на этапы и дорожки. Внутри дорожки задачи идут по очереди и у одного человека.

| Этап | Задачи | Человек | Когда начинать |
|---|---|---|---|
| 1 | 0.1, 3.1 и 2.4 — друг от друга не зависят | до 3 | сразу |
| 2 | 3.2 Зависимости в Poetry | 1 | после 3.1 |
| 3 | Дорожка «Инструменты»: 3.3 → 3.4 → 3.5 → 3.6 | 1 | после 3.2 |
| 3 | Дорожка «Окружение»: 4.1 → 4.2 → 4.3 | 1 | после 3.2, параллельно с «Инструментами» |
| 4 | Дорожка «ML»: 2.1 → 2.2 → 2.3 | 1 | после 3.5 и части 2 |
| 5 | 2.5 Отчёт и материалы для показа | 1, скриншоты от всех | в конце |

При трёх участниках это около 4–6 рабочих дней. Четвёртый участник проверяет PR и собирает материалы для отчёта.

Правила, чтобы не мешать друг другу:
1. Задачу 3.2 делает один человек. Остальные задачи частей 1 и 2 начинаются после её слияния: от неё зависит почти всё.
2. Перед форматированием (3.3) не должно быть открытых PR с изменениями в `.py`: оно переписывает 112 файлов из 127. Поэтому 2.4 сливается до 3.3 либо начинается после неё. PR дорожки «Окружение» форматированию не мешают: в них нет кода.
3. `pyproject.toml` и `poetry.lock` меняет только дорожка «Инструменты», по одной задаче за раз.
4. `Makefile`, `README.md` и `.github/workflows/tests.yml` правят задачи из разных дорожек. PR с такими правками сливаются по одному, перед слиянием подтягивается свежий `master`.

## Что в проекте уже есть
Состояние `master` на коммите `1a869e4` (11.06.2026). Таблица — основа колонки «было» в отчёте.

| Задание | Уже есть | Что добавляет практика |
|---|---|---|
| 3. pre-commit, Poetry, линтеры | `ruff check` настроен, проходит и запускается в CI и командой `make lint`; секция форматирования в `pyproject.toml` | lock-файл с точными версиями; применённое форматирование (сейчас 112 из 127 файлов не по стандарту); проверку типов ML-кода; проверки до коммита (pre-commit) |
| 4. Окружение в Git | инструкция по созданию `venv` в README; `venv/` в `.gitignore`; CI и Docker ставят зависимости из `requirements*.txt` | точные версии всех пакетов; одинаковую установку у разработчика, в CI и в Docker; единую версию Python; установку одной командой |
| 2. Рефакторинг | ~20 тыс. строк тестов, в том числе тесты ML; CI; Docker с HEALTHCHECK и непривилегированным пользователем; JSON-логи, Sentry, Prometheus; шифрование DSN | общий модуль вместо дублей в `ml/`; параметры моделей в конфигурации; эталонные тесты моделей; `ml/` в замере покрытия; проверку секретов при запуске |

---

# Часть 0 · Перед началом: зелёный CI на `master`

| ID | Задача | Размер | Зависит от |
|---|---|---|---|
| 0.1 | Вернуть integration-тесты Iceberg: заменить источник образа MinIO | S | — |

### 0.1 · Вернуть integration-тесты Iceberg: заменить источник образа MinIO (S)

**Контекст.** Образ `minio/minio` удалён из Docker Hub. Семь тестов из `tests/integration/test_db_iceberg.py` скачивают его при запуске и падают с ошибкой `ImageNotFound`, поэтому проверка `tests` на `master` красная. Причина внешняя: 02.08.2026 те же тесты проходили. Проверки на PR не затронуты: `integration` запускается только после слияния в `master`.

**Что сделать**
1. В `tests/integration/test_db_iceberg.py` заменить `MINIO_IMAGE` на общедоступную сборку того же сервера — `cgr.dev/chainguard/minio:latest`. Команда запуска и переменные окружения контейнера не меняются.
2. Проверить исправление запуском `integration` в CI.

**Готово, когда**
- [ ] В CI проходят все тесты из `tests/integration/test_db_iceberg.py`
- [ ] Проверка `tests` на `master` зелёная целиком

**Важно.** Стенд `make iceberg-up` из `docker-compose.yml` использует тот же образ и тоже не запускается. В практику он не входит: замена там требует другой проверки готовности контейнера, потому что в новой сборке нет `curl`.

---

# Часть 1 · Задание 3: pre-commit, Poetry, линтеры

**Цель.** Зависимости описаны в одном месте — `pyproject.toml` и `poetry.lock`. Проверки кода (ruff и mypy) запускаются перед каждым коммитом и в CI, версии инструментов у всех одинаковые.

| ID | Задача | Размер | Зависит от |
|---|---|---|---|
| 3.1 | Подготовка: репозиторий, инструменты, базовые замеры | S | — |
| 3.2 | Зависимости в Poetry | M | 3.1 |
| 3.3 | Форматирование `ruff format` | S | 3.2 |
| 3.4 | Проверка типов mypy для `ml/` | S | 3.3 |
| 3.5 | pre-commit: хуки и проверка в CI | M | 3.4 |
| 3.6 | Команды make и раздел README «Качество кода» | S | 3.5 |

### 3.1 · Подготовка: репозиторий, инструменты, базовые замеры (S)

**Что сделать**
1. В репозитории проверить, что GitHub Actions включены: на вкладке Actions есть прогоны `tests` и `lint`. Задачи плана заведены как issues этого репозитория.
2. Проверить инструменты: Git не ниже 2.31, Python 3.12, Poetry 2.x, Docker.
3. Поставить тег на коммит, с которого началась практика: `git tag practice-start 1a869e4 && git push origin practice-start`.
4. Снять базовые замеры в окружении на CPython 3.12 (не из conda):
   `python3.12 -m venv venv && venv/bin/pip install -r requirements.txt -r requirements-dev.txt`.
   Вывод `venv/bin/pip freeze` сохранить в `docs/practice/baseline-freeze.txt`, замеры — в `docs/practice/baseline.md` вместе с SHA коммита, датой и ОС.

| Метрика | Команда |
|---|---|
| Unit-тесты (passed) | `venv/bin/pytest` |
| Покрытие: общее и `ml/` | `venv/bin/coverage run --source=app,collectors,ml -m pytest`, затем `venv/bin/coverage report --include="app/*,collectors/*"` и `venv/bin/coverage report --include="ml/*"` |
| Неотформатированные файлы | `venv/bin/ruff format --check . \| tail -1` |
| Размер Docker-образа | `docker build -t dbm:baseline . && docker image ls dbm:baseline` |
| Длительность CI | Actions → последний прогон `tests` на `master` |

Ориентиры из ревью от 01.10.2026: 988 passed, покрытие 86 % (`ml/` — 81 %), 112 из 127 файлов не отформатированы.

**Готово, когда**
- [ ] На вкладке Actions есть прогоны workflow
- [ ] `git ls-remote --tags origin practice-start` возвращает SHA, записанный в `baseline.md`
- [ ] `baseline.md` с пятью метриками и `baseline-freeze.txt` закоммичены

### 3.2 · Зависимости в Poetry (M)

**Контекст**
- В `requirements*.txt` 42 пакета закреплены через `==`, часть из них транзитивные. `numpy`, `pandas`, `WTForms`, `clickhouse-driver` импортируются напрямую, но не объявлены. Пакеты `plotly` и `narwhals` не используются: графики строит plotly.js с CDN.
- Диапазон Python — `>=3.12,<3.14`: `numpy` из базового окружения требует Python не ниже 3.12, и с `>=3.11` lock не собирается. README, ruff и Dockerfile уже рассчитаны на 3.12.
- Окружение создаётся в папке проекта (`.venv`): хук pre-commit запоминает путь к интерпретатору, поэтому место окружения фиксируется до установки хуков.
- Процедура проверена на Poetry 2.5.1: lock собирается, в нём 107 пакетов.

**Что сделать**
1. Создать `poetry.toml` и добавить `.venv/` в `.gitignore`:
   ```toml
   [virtualenvs]
   in-project = true
   ```
2. Добавить в `pyproject.toml` блок ниже. Секции `[tool.pytest.ini_options]` и `[tool.ruff*]` сохранить.
   ```toml
   [project]
   name = "db-monitoring"
   version = "0.1.0"
   description = "Система мониторинга данных в БД"
   requires-python = ">=3.12,<3.14"

   [tool.poetry]
   package-mode = false
   requires-poetry = ">=2.0,<3.0"
   ```
3. **Шаг А.** Перенести строки `requirements.txt` в `[project].dependencies` с теми же версиями. Из `requirements-dev.txt` создать группы: `dev` (`pytest`, `coverage`, `ruff`, `playwright`, `pytest-playwright`) и группу `integration` с `optional = true` (`testcontainers[postgres,mysql,clickhouse]`, `boto3`). `playwright` остаётся в `dev`: e2e-тесты импортируют его в начале модулей, и без него pytest не собирает тесты. Выполнить `poetry lock`.
4. **Шаг Б.** Удалить из прямых зависимостей `annotated-types`, `blinker`, `click`, `itsdangerous`, `Jinja2`, `MarkupSafe`, `packaging`, `pydantic_core`, `python-dotenv`, `typing-inspection`, `typing_extensions`, `tzlocal`, `plotly`, `narwhals`. Добавить `numpy`, `pandas`, `WTForms`, `clickhouse-driver` с версиями из `baseline-freeze.txt`. Снова выполнить `poetry lock`: версии, уже записанные в lock, Poetry сохраняет.
5. В `.github/workflows/tests.yml` оставить в матрице `python-version: ["3.12", "3.13"]`. Файлы `requirements*.txt` не трогать: до задачи 4.2 по ним работают CI-тесты и Docker.

**Готово, когда**
- [ ] `poetry check --lock` → `All set!`
- [ ] `poetry install --with dev && poetry run pytest` → число passed как в `baseline.md`. Integration-тесты без своей группы пропускаются: в итоге появится `skipped`
- [ ] `poetry env info --path` выводит `<путь к проекту>/.venv`, `git status` чистый
- [ ] Версии 40 закреплённых пакетов (все, кроме `plotly` и `narwhals`) в `poetry.lock` совпадают с `requirements*.txt`; сверка приложена к PR
- [ ] CI зелёный на 3.12 и 3.13

**Важно.** При активной conda Poetry строит окружение на её Python. Чтобы взять другой интерпретатор, выполнить `poetry env use <путь к python3.12>` и повторить `poetry install --with dev`.

### 3.3 · Форматирование `ruff format` (S)

**Что сделать**
1. Убедиться, что открытых PR нет: после форматирования у них появятся конфликты.
2. Сделать PR с единственным коммитом `poetry run ruff format .` и слить его способом **Create a merge commit** (squash и rebase меняют SHA коммита).
3. Следующим коммитом добавить `.git-blame-ignore-revs` с полным SHA коммита форматирования.

**Готово, когда**
- [ ] `poetry run ruff format --check .` не выводит ни одной строки `Would reformat`
- [ ] `poetry run ruff check .` → `All checks passed!`
- [ ] Тесты зелёные, число passed как в `baseline.md`

### 3.4 · Проверка типов mypy для `ml/` (S)

**Контекст.** В коде есть аннотации типов, но их никто не проверяет. Проверка включается для ML-кода: на `1a869e4` в `ml/` 19 ошибок в трёх файлах, из них 13 — лишние или неполные комментарии `# type: ignore`. Проверка `app/` и `collectors/` (ещё около 25 ошибок) вынесена в бэклог. Задача выполняется после 3.3: обе правят файлы `ml/`, а PR с форматированием требует, чтобы других открытых PR не было.

**Что сделать**
1. `poetry add --group dev mypy`.
2. Добавить в `pyproject.toml`:
   ```toml
   [tool.mypy]
   python_version = "3.12"
   files = ["ml"]
   disallow_untyped_defs = true
   warn_unused_ignores = true
   enable_error_code = ["ignore-without-code"]

   [[tool.mypy.overrides]]
   module = ["app.*"]
   follow_imports = "silent"

   [[tool.mypy.overrides]]
   module = ["sklearn.*", "joblib.*", "prophet.*", "ruptures.*", "pandas.*"]
   ignore_missing_imports = true
   ```
   С `follow_imports = "silent"` типы из `app/` используются, но ошибки в самом `app/` не показываются.
3. Исправить найденные ошибки в `ml/`.

**Готово, когда**
- [ ] `poetry run mypy` → `Success: no issues found`
- [ ] Функция без аннотаций в `ml/` даёт ошибку `no-untyped-def` (проверяется временной правкой)
- [ ] Тесты зелёные

### 3.5 · pre-commit: хуки и проверка в CI (M)

**Что сделать**
1. `poetry add --group dev pre-commit`.
2. Создать `.pre-commit-config.yaml`:
   ```yaml
   repos:
     - repo: https://github.com/pre-commit/pre-commit-hooks
       rev: vX.Y.Z  # последний релиз: выставить командой `poetry run pre-commit autoupdate`
       hooks:
         - id: trailing-whitespace
           args: [--markdown-linebreak-ext=md]
         - id: end-of-file-fixer
         - id: check-yaml
         - id: check-toml
         - id: check-merge-conflict
         - id: check-added-large-files
           args: [--maxkb=1024]
         - id: detect-private-key
     - repo: local
       hooks:
         - id: ruff-check
           name: ruff check
           entry: poetry run ruff check --fix
           language: system
           types: [python]
         - id: ruff-format
           name: ruff format
           entry: poetry run ruff format
           language: system
           types: [python]
         - id: mypy
           name: mypy
           entry: poetry run mypy
           language: system
           types: [python]
           pass_filenames: false
         - id: poetry-check
           name: poetry check --lock
           entry: poetry check --lock
           language: system
           files: ^(pyproject\.toml|poetry\.lock)$
           pass_filenames: false
   ```
3. Выполнить `poetry run pre-commit install`.
4. В `.github/workflows/lint.yml` переименовать job `ruff` в `pre-commit` и заменить его шаги: checkout → `actions/setup-python` с Python 3.12 (параметр `cache: pip` убрать) → `pipx install poetry==<версия из первой строки poetry.lock>` → `poetry install --with dev` → `poetry run pre-commit run --all-files --show-diff-on-failure`. Шаги `pip install ruff==0.9.4` и `make lint` удалить: версия ruff теперь берётся из `poetry.lock`.

**Готово, когда**
- [ ] `poetry run pre-commit run --all-files` → все хуки `Passed`, после прогона `git status` чистый
- [ ] Сценарий 1: испортить форматирование `.py`-файла и выполнить `git commit` → коммит прерван, файл исправлен хуком; после `git add` коммит проходит
- [ ] Сценарий 2: изменить версию пакета в `pyproject.toml` без `poetry lock` → коммит прерван хуком `poetry check --lock`
- [ ] Сценарий 3: добавить ошибку типов в `ml/` → коммит прерван хуком `mypy`
- [ ] Проверка `pre-commit` в PR зелёная; временный коммит с неотформатированным файлом делает её красной (коммит удалён до слияния)
- [ ] `git grep -n "ruff==" .github` → пусто
- [ ] Скриншоты сценариев 1–3 приложены к PR: они нужны для отчёта и показа

### 3.6 · Команды make и раздел README «Качество кода» (S)

**Что сделать**
1. В `Makefile` перевести цели на `poetry run` и добавить недостающие:

   | Цель | Команда |
   |---|---|
   | `lint` | `poetry run ruff check .` |
   | `lint-fix` | `poetry run ruff check . --fix` |
   | `format` | `poetry run ruff format .` |
   | `typecheck` | `poetry run mypy` |
   | `check` | `poetry run pre-commit run --all-files` |
   | `hooks` | `poetry run pre-commit install` |

2. В README добавить раздел «Качество кода»: что проверяет каждый инструмент, команды `make`, команда `git config blame.ignoreRevsFile .git-blame-ignore-revs`.

**Готово, когда**
- [ ] На `master` каждая цель завершается с кодом 0 без активации окружения
- [ ] Раздел «Качество кода» есть в README

### Что показываем по заданию 3
1. `pyproject.toml` с группами зависимостей и `poetry.lock`.
2. Коммит неотформатированного файла прерывается, хук исправляет файл.
3. Правка `pyproject.toml` без `poetry lock` блокирует коммит.
4. Ошибка типов в `ml/` блокирует коммит.
5. Проверка `pre-commit` в PR на GitHub: зелёная, а с намеренной ошибкой — красная.

---

# Часть 2 · Задание 4: интеграция виртуального окружения в Git-репозиторий

**Цель.** Окружение описано файлами в репозитории и одинаково создаётся на машине разработчика, в CI и в Docker. Сама папка `.venv` в репозиторий **не попадает**: в Git хранится её описание.

| Файл в репозитории | Что описывает |
|---|---|
| `pyproject.toml` | зависимости и их группы |
| `poetry.lock` | точные версии и хэши всех пакетов, включая транзитивные |
| `poetry.toml` | окружение создаётся в папке проекта (`.venv`) |
| `requires-python` и `.python-version` | версия Python |
| `.gitignore` | исключает `.venv` и кэши инструментов |

Первые три файла и диапазон Python появляются уже в задаче 3.2: без них не собирается lock. В отчёте они относятся к заданию 4.

| ID | Задача | Размер | Зависит от |
|---|---|---|---|
| 4.1 | Окружение в папке проекта и версия Python | S | 3.2 |
| 4.2 | CI и Docker ставят зависимости из `poetry.lock` | M | 4.1 |
| 4.3 | Установка одной командой и README | S | 4.2 |

### 4.1 · Окружение в папке проекта и версия Python (S)

**Что сделать**
1. Добавить в `.gitignore`: `.mypy_cache/`, `.ruff_cache/`, `.idea/`, `.vscode/`.
2. Создать `.python-version` с содержимым `3.12` (его используют pyenv, uv и IDE).
3. В README указать в требованиях Python 3.12 или 3.13 и обновить бейдж версий (сейчас в нём 3.11, 3.12 и 3.13).
4. Проверить установку в свежем клоне, путь к которому содержит пробел и кириллицу.

**Готово, когда**
- [ ] В свежем клоне `poetry install --with dev` создаёт `.venv` в папке проекта, после установки `git status` чистый
- [ ] `git grep -n "3\.11" -- .github README.md Dockerfile` → пусто
- [ ] IDE (PyCharm или VS Code) предлагает интерпретатор `.venv/bin/python`

### 4.2 · CI и Docker ставят зависимости из `poetry.lock` (M)

**Контекст.** CI-тесты и Docker до сих пор ставят зависимости из `requirements*.txt`, то есть описаний окружения два. Dockerfile остаётся одноэтапным: тестовые пакеты нужны в образе, потому что `make test` запускает тесты в контейнере.

**Что сделать**
1. В `.github/workflows/tests.yml` во всех трёх задачах добавить шаг `pipx install poetry==<версия>`, убрать параметр `cache: pip`, ставить зависимости по таблице и запускать команды через `poetry run`. После установки добавить шаг `poetry run python -V`.

   | Задача | Установка |
   |---|---|
   | `test` | `poetry sync --with dev` |
   | `integration` | `poetry sync --with dev,integration` |
   | `e2e` | `poetry sync --with dev` |

2. Там же добавить триггер `workflow_dispatch` и условие для `integration` и `e2e`:
   `github.event_name == 'workflow_dispatch' || (github.event_name == 'push' && github.ref == 'refs/heads/master')`.
   Сейчас эти задачи запускаются только после слияния в `master`; ручной запуск позволяет проверить их на ветке PR.
3. В `Dockerfile` заменить две строки с `requirements*.txt` на установку из lock:
   ```dockerfile
   COPY --chown=user pyproject.toml poetry.lock poetry.toml ./
   RUN pip install poetry==<версия> \
       && poetry install --with dev --no-root \
       && rm -rf /root/.cache/pypoetry
   ENV PATH=/app/.venv/bin:$PATH
   ```
   Пользователя `user`, блок `ENV`, `HEALTHCHECK` и `CMD` не менять.
4. В `Makefile` в цели `test` взять путь тома в кавычки: `-v "$(CURDIR)/tests:/app/tests"`. Сейчас кавычек нет, и в папке с пробелом в пути команда не работает.
5. В `.dockerignore` добавить файлы, которые уже игнорирует Git: `.env.local`, `env.txt`, `.mcp.json`, `backups/`, `monitor.db.*`.
6. Удалить `requirements.txt` и `requirements-dev.txt` и убрать упоминания о них: комментарий в `lint.yml`, `docs/PROD_CONNECTION_GUIDE.md`, `docs/Architecture.md` (строку 1372 заменить описанием групп Poetry).

**Готово, когда**
- [ ] `test (3.12)` и `test (3.13)` зелёные; `poetry run python -V` в логе показывает версию из матрицы
- [ ] `integration` и `e2e` запущены вручную на ветке PR (Actions → tests → Run workflow) и зелёные
- [ ] `make server` → `curl -s -o /dev/null -w "%{http_code}" localhost:5001/healthz` → `200`
- [ ] `make test` зелёный, в том числе из папки с пробелом в пути; число passed как в `baseline.md`
- [ ] Размер образа записан в PR рядом со значением из `baseline.md`
- [ ] `git grep -n "requirements" -- ':!docs/presentations' ':!docs/practice' ':!README.md'` → пусто

### 4.3 · Установка одной командой и README (S)

**Что сделать**
1. В `Makefile` добавить цели: `install` — проверяет, что Poetry установлен, затем выполняет `poetry sync --with dev` и `poetry run pre-commit install`; `test-local` — `poetry run pytest`. Цели, которые вызывают `pytest` и `python -m` напрямую (`test-integration`, `test-e2e`, запуск скриптов), перевести на `poetry run`: без активированного окружения они берут чужой Python.
2. README, раздел «Установка»: требования (Git 2.31 или новее, Python 3.12 или 3.13, Poetry 2.x, Docker) и шаги `git clone` → `make install` → `cp .env.example .env` → `make test-local`. В разделе «Структура проекта» заменить `requirements.txt` файлами Poetry.
3. README, раздел «Работа с зависимостями»: `poetry add <pkg>`, `poetry add --group dev <pkg>`, `poetry update <pkg>`, `poetry remove <pkg>`; при конфликте в `poetry.lock` — `git checkout --theirs poetry.lock && poetry lock`; вручную lock не редактируется.
4. README, раздел «Проблемы окружения»: активная conda (см. задачу 3.2); после переименования папки проекта — `poetry env remove --all && make install`; хук при коммите отвечает `Executable poetry not found` — в окружении, откуда запущен коммит (например, в IDE), нет пути к Poetry; хук падает с `unknown option 'deduplicate'` — Git старше 2.31.

**Готово, когда**
- [ ] В свежем клоне `make install && make test-local` завершается с кодом 0
- [ ] `git grep -nE "pip install -r|python3 -m venv" -- README.md docs ':!docs/practice'` → пусто

### Что показываем по заданию 4
1. Свежий клон → `make install` → `.venv` в папке проекта, тесты проходят, `git status` чистый.
2. Файлы из таблицы выше: чем описано окружение и почему сама папка `.venv` не хранится в Git.
3. CI и Docker ставят зависимости из `poetry.lock`; файлов `requirements*.txt` в репозитории больше нет.

---

# Часть 3 · Задание 2: рефакторинг кода ML-проекта под production-стандарты

**Цель.** В ML-коде нет дублирования, параметры моделей задаются конфигурацией и проверяются при запуске, а в режиме production приложение не стартует с небезопасными секретами. Результаты моделей при этом не меняются: это подтверждают эталонные тесты.

| ID | Задача | Размер | Зависит от |
|---|---|---|---|
| 2.1 | Эталонные тесты ML | M | часть 2 |
| 2.2 | Общий модуль `ml/common.py` | M | 2.1 |
| 2.3 | Параметры моделей в конфигурации | M | 2.2 |
| 2.4 | Проверка секретов при запуске | S | — |
| 2.5 | Отчёт и материалы для показа | S | все задачи |

### 2.1 · Эталонные тесты ML (M)

**Контекст.** Задачи 2.2 и 2.3 меняют код моделей. Эталонные тесты фиксируют результаты текущего кода и обнаружат любое их изменение.

**Что сделать**
1. Создать `tests/ml_golden/` с наборами данных: `seed = 42`, шаг 15 минут, первая точка — `2026-01-05T00:00:00+00:00`, `null_rate = 0.02`.

   | Набор | Описание |
   |---|---|
   | D1 | стабильный рост: 800 точек, `row_count = 1000 + 10·i + N(0, 5)` |
   | D2 | D1 со всплеском: `row_count × 3` и `null_rate = 0.5` в точках 600–609 |
   | D3 | сдвиг уровня: D1 + 5000, начиная с точки 500 |
   | D4 | короткий ряд: 5 точек |

2. Проверки:

   | Функция | Наборы |
   |---|---|
   | anomaly: `train` + `score_table` | D1, D2; для D4 — `InsufficientDataError` |
   | changepoint: `detect_changepoints` | D1, D3 |
   | forecast, линейная модель | первые 300 точек D1 |
   | forecast, Prophet | D1 |

3. Данные подаются подменами, как в существующих тестах: `get_metrics`, для forecast ещё `get_changepoints` → `[]`, `MODELS_DIR` → `tmp_path`. К базе эталонные тесты не обращаются.
4. Результаты текущего кода сохранить в `tests/ml_golden/expected/`. Сравнение: `rtol = 1e-9`, для Prophet `rtol = 1e-3`. Перед вызовом Prophet выполнять `np.random.seed(42)`: границы интервала он получает случайной выборкой, и без фиксации два прогона расходятся.
5. Добавить цель `make golden-update`, которая перезаписывает эталоны. Обычный `pytest` их не меняет.
6. В `.coveragerc` добавить `ml` в `source`, а в `tests.yml` после `coverage report` — шаг `poetry run coverage report --include="ml/*" --fail-under=80`.

**Готово, когда**
- [ ] `poetry run pytest tests/ml_golden` зелёный локально и в CI; два прогона подряд дают одинаковый результат
- [ ] Временная замена `contamination` с 0.01 на 0.02 роняет тесты anomaly (правка откатывается)
- [ ] В отчёте coverage есть файлы `ml/*`, шаг с порогом 80 % зелёный (сейчас покрытие `ml/` — 81 %)

**Важно.** Совпадение эталона Prophet между macOS и Linux не проверялось. Если эталон, снятый локально, не проходит в CI, пересоздать его в Linux-контейнере или ослабить `rtol` для Prophet (например, до `1e-2`). Решение записать в PR.

### 2.2 · Общий модуль `ml/common.py` (M)

**Контекст.** В `ml/` продублированы `_parse_ts` (3 копии), `MODELS_DIR` (3 копии, одна в `scripts/demo_prepare.py`), `InsufficientDataError` (2 разных класса) и `_model_path` (2 реализации).

**Что сделать**
1. Создать `ml/common.py`: `parse_ts`, `InsufficientDataError`, `MODELS_DIR` и `model_path(kind, table, project_id, metric=None)`. Имена файлов моделей не меняются: функция возвращает те же пути, что и сейчас.
2. В модулях `ml/` заменить копии импортами из `ml.common`. Импорты вида `from ml.forecast import InsufficientDataError` должны продолжать работать.
3. Перевести на `ml.common.MODELS_DIR` остальной код: `app/dashboard.py:280`, `scripts/reset_db.py:21–22`, `scripts/demo_prepare.py:47`.
4. В тестах подмены `MODELS_DIR` перевести на `ml.common.MODELS_DIR`: 8 в `tests/test_anomaly_detector.py`, 11 в `tests/test_forecast.py`, 2 в `tests/test_demo_prepare.py`. Проверки (`assert`) не менять.

**Готово, когда**
- [ ] `git grep -nE "def _?parse_ts|^MODELS_DIR|class InsufficientDataError|def _?model_path" ml scripts` → по одному определению, все в `ml/common.py`
- [ ] Эталонные и остальные тесты зелёные, файлы эталонов не менялись
- [ ] Тест: `ml.forecast.InsufficientDataError is ml.anomaly_detector.InsufficientDataError`
- [ ] Прогон тестов не создаёт файлов в `models/`: число файлов в папке до и после `pytest` одинаково

### 2.3 · Параметры моделей в конфигурации (M)

**Контекст.** Параметры моделей — константы в коде: чтобы изменить порог или число деревьев, нужно править исходники.

**Что сделать**
1. Создать `ml/settings.py` с классом `MLSettings(BaseSettings)` и экземпляром `ml_settings`. В `model_config` указать `env_prefix="ML_"`, `env_file=".env"` и `extra="ignore"`, как у `app.config.Settings`. Значения по умолчанию равны текущим:

   | Модуль | Переменные и значения по умолчанию |
   |---|---|
   | anomaly | `ML_ANOMALY_N_ESTIMATORS` 100, `ML_ANOMALY_CONTAMINATION` 0.01, `ML_ANOMALY_RANDOM_STATE` 42, `ML_ANOMALY_MIN_POINTS` 200, `ML_ANOMALY_TRAIN_WINDOW_DAYS` 60 |
   | forecast | `ML_FORECAST_INTERVAL_WIDTH` 0.95, `ML_FORECAST_WEEKLY_SEASONALITY` true, `ML_FORECAST_DAILY_SEASONALITY` false, `ML_FORECAST_MIN_PROPHET_DAYS` 7, `ML_FORECAST_SEVERE_DROP_RATIO` 0.2 |
   | changepoint | `ML_CHANGEPOINT_PELT_PENALTY` 6.0, `ML_CHANGEPOINT_MIN_SCORE` 1.5, `ML_CHANGEPOINT_MIN_RELATIVE_SHIFT` 0.15, `ML_CHANGEPOINT_WINDOW_DAYS` 14 |
   | drift | `ML_DRIFT_PSI_WARN` 0.2, `ML_DRIFT_PSI_CRITICAL` 0.25, `ML_DRIFT_KS_PVALUE` 0.05, `ML_DRIFT_BASELINE_DAYS` 7 |

   Проверки значений: `ML_ANOMALY_CONTAMINATION` в пределах 0 < x ≤ 0.5, `ML_FORECAST_INTERVAL_WIDTH` в пределах 0 < x < 1, `ML_DRIFT_PSI_WARN` меньше `ML_DRIFT_PSI_CRITICAL`. Остальные константы остаются в коде.
2. Заменить эти константы в `ml/` на поля `ml_settings`. Значения по умолчанию в сигнатурах функций (`window_days=DEFAULT_WINDOW_DAYS`, `baseline_days=BASELINE_DAYS`, `threshold=_SEVERE_DROP_RATIO`) заменить на `None` и читать настройку внутри функции: значение в сигнатуре вычисляется один раз при импорте.
3. В `create_app()` импортировать `ml.settings`, чтобы ошибка конфигурации проявлялась при запуске.
4. В `.env.example` добавить закомментированный блок переменных `ML_*` со значениями по умолчанию.
5. В тестах подмены и ссылки на константы (`ad.MIN_POINTS`, `cp_mod.MIN_SCORE`, `drift_mod.PSI_CRITICAL`) перевести на `ml_settings`. Тесты работают на значениях по умолчанию и не зависят от локального `.env`.

**Готово, когда**
- [ ] Эталонные тесты зелёные без изменения эталонов
- [ ] Тест: при `ML_ANOMALY_CONTAMINATION=0.05` обученная модель имеет `contamination == 0.05`
- [ ] Тест: `ML_ANOMALY_CONTAMINATION=0.6`, а также равные `ML_DRIFT_PSI_WARN` и `ML_DRIFT_PSI_CRITICAL` → `ValidationError`
- [ ] Все переменные из таблицы есть в `.env.example`

**Важно.** Изменённый параметр действует только на заново обученные модели: сохранённые файлы моделей при смене настроек не сбрасываются (это задача «Метаданные в сохранённых моделях» из бэклога). После смены параметра модели переобучаются ночной задачей или командой `make warmup-ml`.

### 2.4 · Проверка секретов при запуске (S)

**Контекст.** В `app/config.py:17` стоит `SECRET_KEY = "dev-secret"`, и при запуске это не проверяется, хотя этим ключом подписываются сессии и CSRF-токены. `FERNET_KEY` (ключ шифрования DSN) не описан в `.env.example` и README.

**Что сделать**
1. В `app/config.py` добавить `is_production()`: режим берётся из переменной окружения `FLASK_ENV`, а если она не задана — из `settings.FLASK_ENV`. Использовать её в `app/crypto.py` вместо собственной проверки.
2. В `create_app()` в режиме production выбрасывать `RuntimeError`, если `SECRET_KEY` пустой, равен `dev-secret` или `change-me-to-something-random`, либо короче 32 символов. Значение ключа в текст ошибки не попадает. Там же сразу проверять `FERNET_KEY`: сейчас он проверяется только при первом шифровании.
3. В `.env.example` и README описать обе переменные с командами генерации: `python -c "import secrets; print(secrets.token_hex(32))"` и `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`.

**Готово, когда**
- [ ] Тест: production и слабый `SECRET_KEY` → `RuntimeError`; production и ключ из 32 символов → запуск; development и `dev-secret` → запуск
- [ ] Тест: production без `FERNET_KEY` → `FernetKeyMissing` при запуске
- [ ] Существующие тесты зелёные без правок, в том числе `tests/test_connections.py`

### 2.5 · Отчёт и материалы для показа (S)

**Что сделать**
1. `docs/practice/REPORT.md`:
   - для каждого задания — таблица «Было | Стало | PR»; колонка «Было» берётся из раздела «Что в проекте уже есть»;
   - слово «добавлено» — только для того, чего не было совсем: lock-файл, pre-commit, mypy, `MLSettings`, эталонные тесты, проверка секретов. Для остального — «доработано», «доведено до конца»;
   - метрики «было / стало» из `baseline.md`, снятые теми же командами;
   - решения с причинами: группы Poetry, отказ от Python 3.11, что вынесено в бэклог.
2. Материалы для показа: по каждому пункту списков «Что показываем» — скриншот или короткая запись экрана.
3. `docs/Architecture.md`: обновить описание зависимостей (Poetry вместо `requirements*.txt`) и добавить раздел про конфигурацию ML (`MLSettings`, `ml/common.py`).

**Готово, когда**
- [ ] В `REPORT.md` есть все четыре пункта, каждая задача связана с PR
- [ ] Ничего из того, что уже было в проекте, не описано как «добавлено»
- [ ] По каждому пункту списков «Что показываем» есть скриншот или запись

### Что показываем по заданию 2
1. Эталонные тесты: изменили параметр модели — тесты красные, вернули — зелёные.
2. `ml/common.py`: было четыре вида дублей, стало по одному определению.
3. Параметры моделей в `.env.example`; `ML_ANOMALY_CONTAMINATION=0.6` → понятная ошибка при запуске.
4. `FLASK_ENV=production` с `SECRET_KEY=dev-secret` → приложение не стартует.
5. Покрытие `ml/` в отчёте CI и порог 80 %.

---

# Бэклог

Задачи ниже усиливают результат, но для покрытия задания не нужны. Задачи из таблицы заведены как issues #15–#23.

**Вынесено из плана**

| Задача | Размер | Почему не в плане |
|---|---|---|
| Дополнительные правила ruff: BLE, C90, T20, PTH | S | ruff уже настроен и проверяет код; новые правила потребуют 57 пометок `noqa` |
| mypy для `app/` и `collectors/` | M | около 25 ошибок вне ML-кода |
| Защита ветки `master`: слияние только через PR с зелёным CI | XS | организационная мера, к пунктам задания не относится |
| Многоэтапный Dockerfile: прод-образ без тестовых пакетов | M | оптимизация образа; установка из lock уже есть в задаче 4.2 |
| Запуск в Docker через gunicorn вместо dev-сервера Flask | M | относится к развёртыванию, а не к коду |
| Новая схема имён файлов моделей; удаление флагов `_HAS_*` | M | меняет имена сохранённых моделей и требует их переобучения |
| Метаданные в сохранённых моделях: параметры и версии библиотек | S | следующий шаг после задачи 2.3 |
| Отделение ML-алгоритмов от хранилища | L | самая объёмная задача: четыре модуля и около 28 подмен в тестах |
| Явная обработка исключений вместо `except Exception` | M | 46 мест в коде |

**Промышленные улучшения**
- Вернуть стенд `make iceberg-up`: в `docker-compose.yml` остался недоступный образ `minio/minio`, а в новой сборке нет `curl` для проверки готовности.
- Отдельный процесс планировщика и несколько воркеров gunicorn. Для этого нужны Redis для Flask-Limiter и обязательный `FERNET_KEY`.
- Атомарная запись файлов моделей (временный файл и `os.replace`).
- Упростить 7 функций со сложностью выше 10, начиная с `collect_for_connection` (сложность 35).
- Разбить `app/metrics_storage.py` (3243 строки) на модули.
- Правила безопасности ruff `S` с разбором 205 срабатываний.
- Удалить пустой пакет `api/`.
- Dependabot для Poetry, GitHub Actions и Docker.
- Первый релиз `v0.1.0`. Тегов в репозитории нет, `release.yml` ещё ни разу не запускался.
