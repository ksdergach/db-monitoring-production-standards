# Отчёт по практике: production-стандарты для db-monitoring

Курс «Бизнес-применение машинного обучения», УрФУ. Репозиторий: <https://github.com/ksdergach/db-monitoring-production-standards>.

Отчёт показывает, что изменилось в проекте по трём пунктам задания. Состояние «было» — коммит `1a869e4` (тег `practice-start`), состояние «стало» — коммит `0828322` в ветке `master`. Постановки задач лежат в [plan.md](plan.md), замеры до начала работы — в [baseline.md](baseline.md).

## Итог

| Пункт задания | Что получилось |
|---|---|
| 3. Настройка pre-commit, Poetry, линтеров | Зависимости описаны в `pyproject.toml` и зафиксированы в `poetry.lock`. Формат, линтер, типы ML-кода и актуальность lock-файла проверяются перед каждым коммитом и в CI. |
| 4. Интеграция виртуального окружения в Git-репозиторий ML-проекта | Окружение описано файлами в репозитории. Одна команда `make install` создаёт его у разработчика, CI и Docker ставят те же версии из `poetry.lock`. |
| 2. Рефакторинг кода ML-проекта под production-стандарты | Дубли в ML-коде сведены в общий модуль, параметры моделей заданы конфигурацией, результаты моделей защищены эталонными тестами, приложение не запускается с небезопасными секретами. |

Закрыты все 15 задач плана и одна задача из бэклога. Слито 14 pull request, включая этот. Каждый прошёл проверки CI.

## Задачи и pull request

| Задача | Что сделано | PR |
|---|---|---|
| 0.1 ([#24]) | Integration-тесты снова зелёные: заменён недоступный образ MinIO | [PR #25] |
| 3.1 ([#1]) | Базовые замеры, план практики, тег `practice-start` | [PR #26] |
| 3.2 ([#2]) | Зависимости в Poetry | [PR #27] |
| 3.3 ([#3]) | Форматирование `ruff format` | [PR #28] |
| 3.4 ([#4]) | Проверка типов mypy для `ml/` | [PR #29] |
| 3.5 ([#5]) | pre-commit: хуки и проверка в CI | [PR #30], демонстрация [PR #31] |
| 3.6 ([#6]) | Команды `make` и раздел README «Качество кода» | [PR #33] |
| 4.1 ([#7]) | Окружение в папке проекта и версия Python | [PR #32] |
| 4.2 ([#8]) | CI и Docker ставят зависимости из `poetry.lock` | [PR #35] |
| 4.3 ([#9]) | Установка одной командой и README | [PR #35] |
| 2.1 ([#10]) | Эталонные тесты ML | [PR #38] |
| 2.2 ([#11]) | Общий модуль `ml/common.py` | [PR #37] |
| 2.3 ([#12]) | Параметры моделей в конфигурации | [PR #39] |
| 2.4 ([#13]) | Проверка секретов при запуске | [PR #34] |
| 2.5 ([#14]) | Отчёт и материалы для показа | этот PR |
| Бэклог ([#17]) | Защита ветки `master` | настройка репозитория, демонстрация [PR #36] |

## Задание 3. pre-commit, Poetry, линтеры

| Было | Стало | PR |
|---|---|---|
| Зависимости лежали в `requirements.txt` и `requirements-dev.txt`: 42 пакета с точными версиями. Lock-файла не было, версии остальных пакетов окружения нигде не записаны. | Зависимости описаны в `pyproject.toml`: 29 прямых, группы `dev` и `integration`. Добавлен lock-файл `poetry.lock`: 122 пакета с точными версиями и контрольными суммами. | [PR #27] |
| `ruff check` настроен, проходит и запускается в CI. Единый формат не применён: 112 файлов из 127 не по стандарту. | Форматирование доведено до конца: `ruff format` применён ко всему коду одним коммитом, неотформатированных файлов нет. Коммит записан в `.git-blame-ignore-revs`. | [PR #28] |
| Аннотации типов в коде есть, но их никто не проверяет. | Добавлена проверка типов mypy для `ml/`. Исправлено 19 ошибок, функция без аннотаций теперь считается ошибкой. | [PR #29] |
| Проверок перед коммитом нет. В CI стиль кода проверяет только `ruff check`. | Добавлен pre-commit: 11 хуков, в том числе `ruff check`, `ruff format`, mypy и `poetry check --lock`. Те же хуки запускает задание `pre-commit` в CI. | [PR #30], [PR #31] |
| Для проверок есть две команды: `make lint` и `make lint-fix`. Обе вызывают ruff напрямую. | Команды `make` доработаны и дополнены: `lint`, `lint-fix`, `format`, `typecheck`, `check`, `hooks` работают через `poetry run`. В README появился раздел «Качество кода». | [PR #33] |
| PR с красной проверкой можно слить, коммит можно отправить прямо в `master`. | Включена защита ветки `master`: изменения только через PR, обязательны проверки `pre-commit`, `test (3.12)` и `test (3.13)`. | [#17], [PR #36] |

## Задание 4. Виртуальное окружение в Git-репозитории

| Было | Стало | PR |
|---|---|---|
| README предлагает создать `venv` вручную и поставить пакеты из `requirements.txt`. В `.gitignore` указана папка `venv/`. | Установка доведена до одной команды: `make install` создаёт `.venv` в папке проекта из `poetry.lock` и включает хуки. Папка `.venv`, кэши mypy и ruff, настройки IDE в Git не попадают. | [PR #32], [PR #35] |
| Версия Python не зафиксирована: в README «3.12+», в CI матрица 3.11–3.13. | Версия зафиксирована: `requires-python = ">=3.12,<3.14"` в `pyproject.toml`. Файл `.python-version` выбирает 3.12 для локальной работы, в CI матрица 3.12 и 3.13. | [PR #27], [PR #32] |
| CI и Docker ставят зависимости из `requirements*.txt`, то есть окружение описано дважды. | CI и Docker переведены на `poetry.lock`: у разработчика, в CI и в образе стоят одни и те же версии. Файлы `requirements*.txt` удалены. | [PR #35] |
| Тесты integration и e2e запускаются только после слияния в `master`. | Их можно запустить вручную на ветке PR. При ручном запуске задание `environment` проверяет установку в свежем клоне, запуск в Docker, `/healthz` и `make test`. | [PR #35] |
| В README нет разделов о работе с зависимостями и о проблемах окружения. | README дополнен разделами «Работа с зависимостями» и «Проблемы окружения». | [PR #35] |

Окружение описывают пять файлов. Сама папка `.venv` в Git не хранится: она занимает около 870 МБ, зависит от платформы и одной командой собирается из lock-файла.

| Файл | Что описывает |
|---|---|
| `pyproject.toml` | зависимости, их группы и диапазон версий Python |
| `poetry.lock` | точные версии и контрольные суммы всех пакетов |
| `poetry.toml` | окружение создаётся в папке проекта (`.venv`) |
| `.python-version` | версия Python для локальной работы |
| `.gitignore` | исключает `.venv` и кэши инструментов |

## Задание 2. Рефакторинг ML-кода

| Было | Стало | PR |
|---|---|---|
| Результаты моделей ничем не зафиксированы: изменение параметра модели тесты не замечают. | Добавлены эталонные тесты `tests/ml_golden/`: 7 проверок на четырёх наборах данных. Изменение параметра модели делает их красными. | [PR #38] |
| В `ml/` четыре вида дублей: `_parse_ts` (3 копии), `MODELS_DIR` (3 копии), `InsufficientDataError` (2 разных класса), `_model_path` (2 реализации). | Дубли сведены в общий модуль `ml/common.py`, у каждого определения одно место. Имена файлов моделей не изменились, переобучать модели не нужно. | [PR #37] |
| Параметры моделей — константы в коде. Чтобы изменить порог, нужно править исходники. | Добавлен класс `MLSettings` (`ml/settings.py`): 18 параметров задаются переменными окружения с префиксом `ML_`. Недопустимое значение останавливает запуск с понятной ошибкой. | [PR #39] |
| `SECRET_KEY` по умолчанию равен `dev-secret`, при запуске это не проверяется. `FERNET_KEY` не описан. | Добавлена проверка секретов при запуске: в режиме production приложение не стартует со слабым `SECRET_KEY` или без `FERNET_KEY`. Обе переменные описаны в `.env.example` и README. | [PR #34] |
| Папка `ml/` не входит в замер покрытия в CI. | `ml/` входит в замер покрытия, в CI установлен порог 80 %. Сейчас покрытие `ml/` — 84 %. | [PR #38] |
| ML-код отформатирован не по стандарту, типы не проверяются. | ML-код приведён к единому формату и проходит проверку типов (см. задание 3). | [PR #28], [PR #29] |

## Метрики «было / стало»

Значения «стало» сняты 04.10.2026 теми же командами и на том же компьютере, что и в `baseline.md`: macOS 26.5.2, arm64, CPython 3.12.7. Вместо `venv/bin/…` команды запускаются через `poetry run`.

| Метрика | Было | Стало | Команда |
|---|---|---|---|
| Unit-тесты | 988 passed | 1029 passed локально, 1030 passed в CI | `poetry run pytest` |
| Покрытие: общее / `ml/` | 86 % / 81 % | 86 % / 84 % | `coverage run --source=app,collectors,ml -m pytest`, затем `coverage report` с `--include` |
| Неотформатированные файлы | 112 из 127 | 0 из 135 | `ruff format --check . \| tail -1` |
| Размер Docker-образа | 1,83 ГБ, в сжатом виде 403 МБ | 1,69 ГБ, в сжатом виде 379 МБ | `docker image ls` |
| Длительность CI | 5 мин 27 с | 5 мин 41 с | Actions → прогон `tests` на `master` |

Пояснения к таблице:

- **Тесты.** Прибавилось 42 теста: 10 для проверки секретов, 7 эталонных, 17 для общего модуля и 8 для настроек моделей. Существующие проверки не менялись. Локально на macOS один эталонный тест пропускается, поэтому там 1029.
- **Размер образа.** В `baseline.md` записано 1,81 ГБ и 399 МБ. По правилу из того же файла образы сравниваются только на одном компьютере. Поэтому в [PR #35] оба образа собраны заново на одном Mac (linux/arm64, Docker 28.5.1): с тега `practice-start` и с ветки PR. После этого PR менялись только Python-файлы ML-кода и тестов, образ заново не измерялся.
- **Длительность CI.** Время меняется от запуска к запуску в пределах минуты, разница 14 секунд в этот разброс укладывается.

## Решения и их причины

- **Группы зависимостей Poetry.** В группе `dev` лежат тесты, линтеры и pre-commit. Пакет `playwright` тоже там: e2e-тесты импортируют его в начале модулей, и без него pytest не может собрать тесты. Группа `integration` необязательная: `testcontainers` и `boto3` нужны только integration-тестам, которым требуется Docker.
- **Отказ от Python 3.11.** Lock-файл один на все поддерживаемые версии, а четыре пакета из него (`numpy`, `scipy`, `contourpy`, `deprecated`) требуют Python 3.12. С диапазоном от 3.11 команда `poetry lock` завершается ошибкой. README и Docker-образ проекта и раньше были рассчитаны на 3.12.
- **Форматирование одним коммитом.** Изменилось 112 файлов. Чтобы убедиться, что поменялся только внешний вид, сравнивались синтаксические деревья всех файлов до и после. Коммит записан в `.git-blame-ignore-revs`, и `git blame` его пропускает.
- **mypy только для `ml/`.** Задание относится к ML-коду. В остальном коде около 25 ошибок типов, их исправление вынесено в бэклог.
- **Хуки запускают инструменты через Poetry.** Версии ruff, mypy и pre-commit берутся из `poetry.lock`, поэтому результат на компьютере разработчика совпадает с CI.
- **Один этап в Dockerfile.** Группа `dev` ставится в образ, потому что `make test` запускает тесты в контейнере. Образ без тестовых пакетов вынесен в бэклог.
- **Эталон Prophet проверяется только в CI.** На macOS результат Prophet отличается от Linux до 0,2 %. Ослаблять допуск до 1 % не стали: с ним тест перестаёт замечать смену настроек модели. Поэтому этот один тест запускается только на Linux x86_64, то есть в CI.
- **Прежние имена файлов моделей.** Общая функция `model_path` возвращает те же пути, что и раньше, поэтому сохранённые модели не нужно переобучать. Новая схема имён вынесена в бэклог.
- **Защита ветки без обязательных одобрений.** Правило требует PR и зелёные проверки, но не требует одобрения: команда маленькая, и ожидание ревью задерживало бы слияние. Ревью проводилось по договорённости.

## Что вынесено в бэклог

| Задача | Почему не в плане |
|---|---|
| [#15] Дополнительные правила ruff | ruff уже проверяет код, новые правила потребовали бы 57 пометок `noqa` |
| [#16] mypy для `app/` и `collectors/` | около 25 ошибок вне ML-кода |
| [#18] Многоэтапный Dockerfile | оптимизация образа; установка из lock-файла уже сделана |
| [#19] Запуск в Docker через gunicorn | относится к развёртыванию, а не к коду |
| [#20] Новая схема имён файлов моделей | меняет имена сохранённых моделей и требует их переобучения |
| [#21] Метаданные в сохранённых моделях | следующий шаг после настроек моделей |
| [#22] Отделение ML-алгоритмов от хранилища | самая объёмная задача: четыре модуля и около 28 подмен в тестах |
| [#23] Явная обработка исключений | 46 мест в коде |

Задача [#17] «Защита ветки `master`» тоже была в бэклоге, но выполнена.

## Материалы для показа

По каждому пункту материала для демонстрации на защите есть картинка. Картинки собраны из настоящего вывода команд в терминале; это не снимки экрана. Пропущенные строки вывода помечены.

**Задание 3**

| Материал для демонстрации на защите | Картинка |
|---|---|
| 1. `pyproject.toml` с группами зависимостей и `poetry.lock` | [demo-3-1-poetry-files.png](images/demo-3-1-poetry-files.png) |
| 2. Коммит неотформатированного файла прерывается, хук исправляет файл | [3.5-scenario-1-format.png](images/3.5-scenario-1-format.png) |
| 3. Правка `pyproject.toml` без `poetry lock` блокирует коммит | [3.5-scenario-2-lock.png](images/3.5-scenario-2-lock.png) |
| 4. Ошибка типов в `ml/` блокирует коммит | [3.5-scenario-3-types.png](images/3.5-scenario-3-types.png) |
| 5. Проверка `pre-commit` в PR: зелёная, а с намеренной ошибкой — красная | [demo-3-5-ci-check.png](images/demo-3-5-ci-check.png), страницы [PR #30] и [PR #31] |

**Задание 4**

| Материал для демонстрации на защите | Картинка |
|---|---|
| 1. Свежий клон → `make install` → `.venv` в папке проекта, тесты проходят, `git status` чистый | [demo-4-1-fresh-clone.png](images/demo-4-1-fresh-clone.png) |
| 2. Чем описано окружение и почему папка `.venv` не хранится в Git | [demo-4-2-environment-files.png](images/demo-4-2-environment-files.png) |
| 3. CI и Docker ставят зависимости из `poetry.lock`, файлов `requirements*.txt` нет | [demo-4-3-lock-in-ci-docker.png](images/demo-4-3-lock-in-ci-docker.png) |

**Задание 2**

| Материал для демонстрации на защите | Картинка |
|---|---|
| 1. Эталонные тесты: изменили параметр модели — красные, вернули — зелёные | [demo-2-1-golden-tests.png](images/demo-2-1-golden-tests.png) |
| 2. `ml/common.py`: было четыре вида дублей, стало по одному определению | [demo-2-2-common-module.png](images/demo-2-2-common-module.png) |
| 3. Параметры моделей в `.env.example`; недопустимое значение — понятная ошибка при запуске | [demo-2-3-ml-settings.png](images/demo-2-3-ml-settings.png) |
| 4. `FLASK_ENV=production` с `SECRET_KEY=dev-secret` — приложение не стартует | [demo-2-4-production-secrets.png](images/demo-2-4-production-secrets.png) |
| 5. Покрытие `ml/` в отчёте CI и порог 80 % | [demo-2-5-ml-coverage.png](images/demo-2-5-ml-coverage.png) |

[#1]: https://github.com/ksdergach/db-monitoring-production-standards/issues/1
[#2]: https://github.com/ksdergach/db-monitoring-production-standards/issues/2
[#3]: https://github.com/ksdergach/db-monitoring-production-standards/issues/3
[#4]: https://github.com/ksdergach/db-monitoring-production-standards/issues/4
[#5]: https://github.com/ksdergach/db-monitoring-production-standards/issues/5
[#6]: https://github.com/ksdergach/db-monitoring-production-standards/issues/6
[#7]: https://github.com/ksdergach/db-monitoring-production-standards/issues/7
[#8]: https://github.com/ksdergach/db-monitoring-production-standards/issues/8
[#9]: https://github.com/ksdergach/db-monitoring-production-standards/issues/9
[#10]: https://github.com/ksdergach/db-monitoring-production-standards/issues/10
[#11]: https://github.com/ksdergach/db-monitoring-production-standards/issues/11
[#12]: https://github.com/ksdergach/db-monitoring-production-standards/issues/12
[#13]: https://github.com/ksdergach/db-monitoring-production-standards/issues/13
[#14]: https://github.com/ksdergach/db-monitoring-production-standards/issues/14
[#15]: https://github.com/ksdergach/db-monitoring-production-standards/issues/15
[#16]: https://github.com/ksdergach/db-monitoring-production-standards/issues/16
[#17]: https://github.com/ksdergach/db-monitoring-production-standards/issues/17
[#18]: https://github.com/ksdergach/db-monitoring-production-standards/issues/18
[#19]: https://github.com/ksdergach/db-monitoring-production-standards/issues/19
[#20]: https://github.com/ksdergach/db-monitoring-production-standards/issues/20
[#21]: https://github.com/ksdergach/db-monitoring-production-standards/issues/21
[#22]: https://github.com/ksdergach/db-monitoring-production-standards/issues/22
[#23]: https://github.com/ksdergach/db-monitoring-production-standards/issues/23
[#24]: https://github.com/ksdergach/db-monitoring-production-standards/issues/24
[PR #25]: https://github.com/ksdergach/db-monitoring-production-standards/pull/25
[PR #26]: https://github.com/ksdergach/db-monitoring-production-standards/pull/26
[PR #27]: https://github.com/ksdergach/db-monitoring-production-standards/pull/27
[PR #28]: https://github.com/ksdergach/db-monitoring-production-standards/pull/28
[PR #29]: https://github.com/ksdergach/db-monitoring-production-standards/pull/29
[PR #30]: https://github.com/ksdergach/db-monitoring-production-standards/pull/30
[PR #31]: https://github.com/ksdergach/db-monitoring-production-standards/pull/31
[PR #32]: https://github.com/ksdergach/db-monitoring-production-standards/pull/32
[PR #33]: https://github.com/ksdergach/db-monitoring-production-standards/pull/33
[PR #34]: https://github.com/ksdergach/db-monitoring-production-standards/pull/34
[PR #35]: https://github.com/ksdergach/db-monitoring-production-standards/pull/35
[PR #36]: https://github.com/ksdergach/db-monitoring-production-standards/pull/36
[PR #37]: https://github.com/ksdergach/db-monitoring-production-standards/pull/37
[PR #38]: https://github.com/ksdergach/db-monitoring-production-standards/pull/38
[PR #39]: https://github.com/ksdergach/db-monitoring-production-standards/pull/39
