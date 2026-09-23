<div align="center">

# RAG Document Search Service

### An asynchronous document-ingestion and retrieval backend with vector, full-text, reranked, and hybrid search.

The service stores Markdown documents in PostgreSQL, processes them asynchronously,
and exposes multiple retrieval strategies through a FastAPI API. Documents are split
by heading structure, embedded with Qwen, and indexed with both pgvector and PostgreSQL
full-text search.

[![Python 3.14](https://img.shields.io/badge/Python-3.14-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.116+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL 16](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![pgvector](https://img.shields.io/badge/vector_search-pgvector-4169E1)](https://github.com/pgvector/pgvector)
[![RabbitMQ](https://img.shields.io/badge/queue-RabbitMQ_4-FF6600?logo=rabbitmq&logoColor=white)](https://www.rabbitmq.com/)
[![gRPC](https://img.shields.io/badge/internal_API-gRPC-244C5A?logo=google&logoColor=white)](https://grpc.io/)
[![Ruff](https://img.shields.io/badge/lint-Ruff-D7FF64?logo=ruff&logoColor=black)](https://docs.astral.sh/ruff/)
[![mypy](https://img.shields.io/badge/types-mypy-2A6DB2)](https://mypy-lang.org/)

</div>

---

> [!CAUTION]
> The HTTP API does not currently provide authentication, authorization, rate
> limiting, or tenant isolation. Do not expose it directly to untrusted clients.
> Production deployments should place it behind an authenticated gateway and apply
> appropriate network, secret-management, audit, and data-retention controls.

## What it does

| Capability | Description |
|---|---|
| Asynchronous ingestion | Stores a document immediately, then publishes a durable RabbitMQ task for processing. |
| Structure-aware chunking | Splits Markdown by `#`, `##`, and `###` headings while preserving the heading hierarchy in every chunk. |
| Vector search | Retrieves up to 30 chunks by cosine distance using 1,024-dimensional Qwen embeddings and pgvector. |
| Full-text search | Ranks up to 30 chunks with PostgreSQL full-text search. |
| Reranked search | Retrieves 30 vector candidates and returns the best 5 using `Qwen/Qwen3-Reranker-0.6B`. |
| Hybrid search | Fuses full-text and vector results with Reciprocal Rank Fusion, then reranks the combined candidates. |
| Isolated search worker | Keeps embedding and reranking models behind an internal asynchronous gRPC service. |

## How it works

```mermaid
flowchart LR
    A["Client"] -->|"POST /documents"| B["FastAPI"]
    B --> C["PostgreSQL"]
    B --> D["RabbitMQ"]
    D --> E["Ingestion worker"]
    E --> F["Markdown chunker"]
    F --> G["Qwen embedding model"]
    G --> C

    A -->|"Search request"| B
    B -->|"gRPC"| H["Search worker"]
    H --> I["Vector search"]
    H --> J["Full-text search"]
    I --> K["Qwen reranker"]
    J --> L["Reciprocal Rank Fusion"]
    I --> L
    L --> K
    I --> C
    J --> C
```

Document ingestion follows this sequence:

1. The API validates and stores the document in PostgreSQL.
2. It publishes the document ID to a durable RabbitMQ queue.
3. The ingestion worker loads the document and splits it into token-bounded chunks.
4. The worker creates embeddings with `Qwen/Qwen3-Embedding-0.6B`.
5. It atomically replaces the document's chunks and 1,024-dimensional vectors.

Search requests are forwarded from FastAPI to the search worker over gRPC. The search
worker owns the embedding and reranking models and queries PostgreSQL directly.

## Architecture

The code follows a small layered architecture:

```text
Router -> Service -> Repository -> PostgreSQL
              |
              +-> RabbitMQ / gRPC
```

- **Routers** validate HTTP input and map application errors to HTTP responses.
- **Services** contain document-ingestion and retrieval business logic.
- **Repositories** contain SQLAlchemy 2 async database access.
- **Workers** consume ingestion tasks and serve search requests.
- **Contracts** define the internal gRPC API shared by FastAPI and the search worker.

Database schema changes are managed with Alembic. The application does not call
`create_all`; migrations must be applied explicitly before startup.

## Quick start with Docker

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) with Compose
- Enough disk space and memory for the embedding and reranker models
- Internet access on the first worker startup to download models from Hugging Face

### 1. Configure the environment

```bash
cp .env.example .env
```

At minimum, replace `POSTGRES_PASSWORD` and `RABBITMQ_PASSWORD` in `.env`.
The remaining values provide a working local configuration.

### 2. Build the images and start the infrastructure

```bash
docker compose build api worker search-worker
docker compose up -d postgres rabbitmq
```

### 3. Apply database migrations

```bash
docker compose run --rm api alembic upgrade head
```

### 4. Start the application

```bash
docker compose up -d api worker search-worker
```

The services are then available at:

- API: <http://localhost:8000>
- Swagger UI: <http://localhost:8000/docs>
- RabbitMQ Management: <http://localhost:15672>

The first worker startup downloads the embedding and reranker models. They are cached
in the `huggingface_cache` Docker volume, so later starts do not download them again.

Inspect or stop the stack with:

```bash
docker compose logs -f api worker search-worker
docker compose down
```

`docker compose down` preserves named volumes. Add `--volumes` only when you
intentionally want to delete the PostgreSQL data and model cache.

## API

All endpoints accept and return JSON. Search endpoints return `503 Service Unavailable`
when the gRPC search worker cannot be reached.

### Create a document

`POST /documents` stores a document and queues it for asynchronous processing.

```bash
curl -X POST http://localhost:8000/documents \
  -H 'Content-Type: application/json' \
  -d '{
    "document_number": "FAQ-001",
    "context": "# Delivery\n## How long does delivery take?\n### Answer\nStandard delivery takes 3–5 business days."
  }'
```

A successful request returns `201 Created`. A duplicate `document_number` returns
`409 Conflict`; blank fields return `422 Unprocessable Entity`.

The chunker is designed for Markdown with this hierarchy:

```markdown
# Topic
## Question
### Answer
Answer text.
```

Each chunk retains its active headings. Content longer than `CHUNK_MAX_TOKENS` is
split into overlapping windows.

### Search endpoints

| Method | Path | Result |
|---|---|---|
| `POST` | `/search` | Up to 30 chunks ordered by cosine distance |
| `POST` | `/fts` | Up to 30 chunks ordered by PostgreSQL full-text rank |
| `POST` | `/reranker` | The best 5 of 30 vector candidates, ordered by reranker score |
| `POST` | `/hybrid_search` | The best 5 fused vector and full-text candidates, ordered by reranker score |

All four endpoints use the same request body:

```json
{
  "question": "How long does delivery take?"
}
```

Vector-search example:

```bash
curl -X POST http://localhost:8000/search \
  -H 'Content-Type: application/json' \
  -d '{"question":"How long does delivery take?"}'
```

Hybrid-search example:

```bash
curl -X POST http://localhost:8000/hybrid_search \
  -H 'Content-Type: application/json' \
  -d '{"question":"How long does delivery take?"}'
```

Every result identifies the source with `document_id`, `document_number`, and
`chunk_number`. Depending on the endpoint, it also includes `distance`, `rank`,
`rrf_score`, or `reranker_score`.

## Configuration

| Variable | Default/example | Purpose |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg://rag_user:...@localhost:5432/rag_db` | Async PostgreSQL connection |
| `RABBITMQ_URL` | `amqp://rag_user:...@localhost:5672/` | RabbitMQ connection |
| `DOCUMENT_CHUNKING_QUEUE` | `document.chunking` | Ingestion queue name |
| `SEARCH_WORKER_TARGET` | `localhost:50051` | Search worker gRPC address used by the API |
| `GRPC_HOST` | `0.0.0.0` | Search worker bind address |
| `GRPC_PORT` | `50051` | Search worker port |
| `EMBEDDING_MODEL` | `Qwen/Qwen3-Embedding-0.6B` | Embedding model; must produce 1,024 dimensions |
| `EMBEDDING_DEVICE` | `cpu` | Embedding inference device |
| `EMBEDDING_BATCH_SIZE` | `8` | Embedding batch size |
| `RERANKER_MODEL` | `Qwen/Qwen3-Reranker-0.6B` | Cross-encoder reranker model |
| `RERANKER_DEVICE` | `cpu` | Reranker inference device |
| `RERANKER_BATCH_SIZE` | `4` | Reranker batch size |
| `CHUNK_MAX_TOKENS` | `300` | Maximum tokens per chunk |
| `CHUNK_OVERLAP_TOKENS` | `30` | Token overlap between adjacent long chunks |

Infrastructure image, port, restart-policy, and health-check settings are documented
in `.env.example` and consumed by `compose.yaml`.

## Running without Docker

Install [uv](https://docs.astral.sh/uv/), start reachable PostgreSQL with pgvector and
RabbitMQ instances, and create `.env` from the example. Then install dependencies and
apply migrations:

```bash
uv sync --extra dev --extra worker
uv run alembic upgrade head
```

Run each process in its own terminal:

```bash
uv run uvicorn app.main:app --reload
```

```bash
uv run python -m worker.main
```

```bash
uv run python -m search_worker.main
```

## Project structure

```text
.
├── alembic/                  Database migrations
├── src/
│   ├── app/                  FastAPI API, services, repositories, and messaging
│   ├── contracts/            Protobuf search contract and generated Python code
│   ├── worker/               Document chunking and embedding worker
│   └── search_worker/        gRPC vector, FTS, reranking, and hybrid search service
├── tests/                    Unit and API tests
├── compose.yaml              Local multi-container stack
├── Dockerfile                API and worker build targets
└── pyproject.toml            Dependencies and tool configuration
```

## Development

Install all development dependencies:

```bash
uv sync --extra dev --extra worker
```

Run the full quality gate:

```bash
uv run ruff check .
uv run mypy .
uv run pytest
```

When the protobuf contract changes, regenerate the Python bindings before committing
the change.

## Current limitations

- The API has no built-in authentication, authorization, rate limiting, or tenant isolation.
- Document processing is asynchronous, but the API does not expose processing status.
- Failed ingestion tasks are requeued without a dedicated dead-letter workflow.
- Search limits and the RRF constant are currently fixed in application code.
- The database schema requires 1,024-dimensional embeddings.
- CPU inference is the default and may be slow for larger workloads.
- The service provides retrieval only; it does not generate answers with an LLM.

Treat these as deployment and integration requirements before using the service in
production.
