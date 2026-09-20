# Document ingestion service

Асинхронный FastAPI-сервис для сохранения номера документа и его текстового
контекста в PostgreSQL. База работает на образе pgvector и заранее включает
расширение `vector` через Alembic; embedding-колонки пока нет.

## Запуск

Скопируйте `.env.example` в `.env`, замените пароль, затем соберите контейнеры
и запустите базу данных:

```bash
docker compose build api
docker compose up -d postgres
docker compose run --rm api alembic upgrade head
docker compose up -d api
```

API будет доступно на `http://localhost:8000`, Swagger UI — на
`http://localhost:8000/docs`.

Миграции намеренно не применяются при старте API. После появления новой
миграции выполните:

```bash
docker compose run --rm api alembic upgrade head
```

## API

```bash
curl -X POST http://localhost:8000/documents \
  -H 'Content-Type: application/json' \
  -d '{"document_number":"001-A","context":"Текст документа"}'
```

Успешный запрос возвращает `201 Created`. Повторный `document_number`
возвращает `409 Conflict`, пустые значения — `422 Unprocessable Entity`.

## Локальная разработка

Установите зависимости и задайте строку подключения:

```bash
uv sync --extra dev
export DATABASE_URL='postgresql+psycopg://rag_user:password@localhost:5432/rag_db'
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

Проверки:

```bash
uv run ruff check .
uv run mypy .
uv run pytest
```
