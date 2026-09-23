# Document ingestion service

Асинхронный FastAPI-сервис для сохранения документов в PostgreSQL. После
создания документа API публикует в RabbitMQ задание на чанкинг. Отдельный
worker читает документ, делит Markdown по структуре `#` / `##` / `###`,
создаёт embeddings моделью `Qwen/Qwen3-Embedding-0.6B` и сохраняет чанки в
PostgreSQL. Длинные ответы делятся максимум по 300 токенов с overlap 30.
Отдельный `search-worker` принимает вопросы от API по gRPC, строит embedding
той же моделью и возвращает три ближайших чанка по cosine distance.

## Запуск

Скопируйте `.env.example` в `.env`, замените пароль, затем соберите контейнеры
и запустите инфраструктуру:

```bash
docker compose build api worker search-worker
docker compose up -d postgres rabbitmq
docker compose run --rm api alembic upgrade head
docker compose up -d api worker search-worker
```

При первом старте worker загрузит модель размером около 1.2 GB. Файлы модели
сохраняются в Docker volume `huggingface_cache`.

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

Для семантического поиска по уже обработанным документам:

```bash
curl -X POST http://localhost:8000/search \
  -H 'Content-Type: application/json' \
  -d '{"question":"Какой срок действия договора?"}'
```

API передаёт вопрос в `search-worker` по gRPC. Ответ содержит до трёх чанков,
отсортированных от наиболее близкого к менее близкому, вместе с
`document_id`, `document_number`, `chunk_number` и cosine distance.

Ожидаемая структура текста документа:

```markdown
# Тема раздела
## Конкретный вопрос
### Ответ или информация
Текст ответа.
```

Каждый сохранённый чанк содержит заголовки темы, вопроса и ответа, чтобы не
терять контекст при поиске.

## Локальная разработка

Установите зависимости и задайте строку подключения:

```bash
uv sync --extra dev --extra worker
export DATABASE_URL='postgresql+psycopg://rag_user:password@localhost:5432/rag_db'
export RABBITMQ_URL='amqp://rag_user:password@localhost:5672/'
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
# В другом терминале:
uv run python -m worker.main
# И ещё в одном терминале:
uv run python -m search_worker.main
```

Проверки:

```bash
uv run ruff check .
uv run mypy .
uv run pytest
```
