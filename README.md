# Keitaro Wrapper

Обёртка над [Keitaro](https://keitaro.io) Admin API:

1. **Создатель кампаний** — по названию, гео и офферу создаёт кампанию с двумя потоками:
   - поток 1: фильтр «страна = GEO» → редирект на `https://www.google.com`;
   - поток 2: без фильтров → оффер(ы).
   Домен, группа и источник трафика выбираются из списков, которые подгружаются из Keitaro.
2. **Редактор кампании** — добавление и удаление офферов. Доли делятся поровну и всегда дают ровно 100%.

Стек: FastAPI, SQLAlchemy 2 (async), PostgreSQL 16, Alembic, httpx. Фронтенд — один HTML-файл на чистом JS (`app/static/index.html`).

## Структура проекта

```
app/
  main.py                      # FastAPI, обработчики ошибок, отдача фронта
  routers.py                   # эндпоинты /api/...
  schemas.py                   # Pydantic-схемы
  models.py                    # SQLAlchemy-модели (Campaign, Offer)
  database.py                  # engine и сессии
  keitaro_client.py            # клиент Keitaro Admin API
  services/campaign_service.py # бизнес-логика (создание, add/remove оффера)
  static/index.html            # интерфейс
migrations/                    # Alembic
docker/                        # Dockerfile и entrypoint.sh
docker-compose.yml
```

## Как это работает

- **Источник правды по офферам — Keitaro.** Таблица офферов и доли в интерфейсе читаются из потока в Keitaro, локальная БД хранит связку «наша кампания → id кампании и потока в Keitaro» и список офферов.
- **Создание кампании.** Сначала создаётся кампания в Keitaro, затем два потока, затем запись в БД. Если шаг падает, созданная в Keitaro кампания удаляется (Keitaro при этом отправляет её в архив, подробнее в разделе «Проблемы»).
- **Доли.** При добавлении/удалении оффера доли пересчитываются поровну, остаток от деления получают первые офферы (3 оффера → 34/33/33).
- **Ограничения.** Нельзя добавить оффер дважды и нельзя удалить последний оффер кампании.

## Быстрый старт (Docker)

Нужны Docker и Docker Compose.

1. Создай `.env`:
   ```bash
   cp .env.example .env
   ```
2. Заполни:
   ```env
   KEITARO_URL=https://tlgk.host
   KEITARO_API_KEY=твой-ключ
   ```
   `DATABASE_URL` для Docker задан в `docker-compose.yml`, в `.env` для него ничего писать не нужно.
3. Запусти:
   ```bash
   docker compose up --build
   ```
4. Открой:
   - http://localhost:8000 — интерфейс
   - http://localhost:8000/docs — Swagger
   - http://localhost:8000/health — проверка живости

Миграции применяются автоматически при старте контейнера (`docker/entrypoint.sh` → `alembic upgrade head`).

Остановка:
```bash
docker compose down        # остановить, база сохранится
docker compose down -v     # остановить и стереть базу
```

## Запуск без Docker

Нужны Python 3.12+ и PostgreSQL.

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt

docker compose up -d db              # Postgres из compose (или свой)

export DATABASE_URL=postgresql+asyncpg://keitaro:keitaro@localhost:5432/keitaro_wrapper
export KEITARO_URL=https://tlgk.host
export KEITARO_API_KEY=твой-ключ     # Windows PowerShell: $env:KEITARO_API_KEY="..."

alembic upgrade head
uvicorn app.main:app --reload
```

## Миграции

Конфигурация берёт `DATABASE_URL` из переменных окружения (`migrations/env.py`).

В Docker:
```bash
docker compose exec app alembic upgrade head                          # применить
docker compose exec app alembic current                               # текущая ревизия
docker compose exec app alembic history                               # список ревизий
docker compose exec app alembic revision --autogenerate -m "описание" # создать после правок models.py
docker compose exec app alembic downgrade -1                          # откатить последнюю
```

Локально те же команды без `docker compose exec app`.

Новый файл миграции создаётся внутри контейнера. Чтобы он появился в проекте, должна быть смонтирована папка `migrations` (см. раздел про монтирование). Сгенерированную миграцию всегда просматривай глазами перед применением.

## Как залезть в базу 
http://localhost:8080
Параметры подключения (из `docker-compose.yml`):

| Параметр | Значение |
|---|---|
| Хост | `localhost` |
| Порт | `5432` |
| Пользователь | `keitaro` |
| Пароль | `keitaro` |
| База | `keitaro_wrapper` |

**Через psql в контейнере** (ничего не нужно ставить):
```bash
docker compose exec db psql -U keitaro -d keitaro_wrapper
```

Полезные команды внутри psql:
```
\dt                     -- список таблиц
\d campaigns            -- структура таблицы
\q                      -- выйти
```

Запросы:
```sql
SELECT * FROM campaigns ORDER BY id DESC;
SELECT * FROM offers;

-- офферы с названием кампании
SELECT c.name, c.geo, o.keitaro_offer_id
FROM offers o JOIN campaigns c ON c.id = o.campaign_id
ORDER BY c.id, o.id;
```

**Через GUI** (DBeaver, DataGrip, TablePlus, IDE): создай подключение PostgreSQL с параметрами из таблицы выше. В DataGrip/IDE на JDBC-строке это `jdbc:postgresql://localhost:5432/keitaro_wrapper`.

Таблицы:
- `campaigns` — `id`, `name`, `geo`, `keitaro_campaign_id`, `keitaro_domain_id`, `keitaro_group_id`, `keitaro_source_id`, `offer_stream_id` (id потока с офферами в Keitaro);
- `offers` — `id`, `campaign_id` (→ `campaigns.id`), `keitaro_offer_id`; пара (`campaign_id`, `keitaro_offer_id`) уникальна.

Если порт 5432 на машине уже занят локальным Postgres, измени проброс в `docker-compose.yml` на `"5433:5432"` и подключайся к порту 5433.

## API

| Метод | Путь | Что делает |
|---|---|---|
| GET | `/api/keitaro/offers` | офферы из Keitaro |
| GET | `/api/keitaro/domains` | домены |
| GET | `/api/keitaro/groups` | группы кампаний |
| GET | `/api/keitaro/sources` | источники трафика |
| POST | `/api/campaigns` | создать кампанию |
| GET | `/api/campaigns` | список кампаний |
| GET | `/api/campaigns/{id}/offers` | офферы кампании с долями |
| POST | `/api/campaigns/{id}/offers` | добавить оффер |
| DELETE | `/api/campaigns/{id}/offers/{offer_id}` | удалить оффер |

Пример создания кампании:
```bash
curl -X POST http://localhost:8000/api/campaigns \
  -H "Content-Type: application/json" \
  -d '{"name":"test_campaign","geo":"NL","offer_id":4518,"domain_id":1813,"group_id":9799,"source_id":836}'
```

Здесь `{id}` — внутренний id кампании из нашей БД, а `offer_id` — id оффера в Keitaro.

## Возможные проблемы

| Симптом | Причина и решение |
|---|---|
| `No config file 'alembic.ini' found` | В образе старая версия проекта. Пересобери: `docker compose build --no-cache`, затем `docker compose up` |
| Пустые списки, ошибка про Keitaro вверху страницы | Неверный `KEITARO_URL` или ключ. Исправь `.env` и перезапусти `docker compose up` |
| `Name has already been used in the archive` | Кампания с таким названием уже лежит в архиве Keitaro (в том числе после отката неудачного создания). Удали её из архива в Keitaro или выбери другое название |
| `Alias is required` / `Action Type is required` | Keitaro требует это поле. В актуальной версии кода оно передаётся, обнови код и перезапусти |
| Ошибка 502 в ответе API | Keitaro вернул ошибку или недоступен. Текст ошибки Keitaro приходит в поле `detail` |
| Контейнер `app` постоянно перезапускается | Смотри логи: `docker compose logs -f app` |