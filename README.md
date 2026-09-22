# Document ingestion service

Асинхронный FastAPI-сервис для сохранения документов в PostgreSQL. После
создания документа API публикует в RabbitMQ задание на чанкинг. Отдельный
worker уже принимает и подтверждает эти задания, но пока не разбивает текст
на чанки и не создаёт embeddings.

## Запуск

Скопируйте `.env.example` в `.env`, замените пароль, затем соберите контейнеры
и запустите инфраструктуру:

```bash
docker compose build api worker
docker compose up -d postgres rabbitmq
docker compose run --rm api alembic upgrade head
docker compose up -d api worker
```

API будет доступно на `http://localhost:8000`, Swagger UI — на
`http://localhost:8000/docs`, RabbitMQ Management — на
`http://localhost:15672`.

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
export RABBITMQ_URL='amqp://rag_user:password@localhost:5672/'
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
# В другом терминале:
uv run python -m worker.main
```

Проверки:

```bash
uv run ruff check .
uv run mypy .
uv run pytest
```
