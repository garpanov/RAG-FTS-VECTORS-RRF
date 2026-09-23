from typing import Any, cast

import pytest

from worker.embeddings import QwenEmbeddingModel


class StubArray:
    def tolist(self) -> list[list[float]]:
        return [[0.5] * 1024]


class StubModel:
    def __init__(self) -> None:
        self.kwargs: dict[str, Any] | None = None

    def encode(self, texts: list[str], **kwargs: Any) -> StubArray:
        assert texts == ["question"]
        self.kwargs = kwargs
        return StubArray()


def make_embedding_model(model: StubModel) -> QwenEmbeddingModel:
    embedding_model = object.__new__(QwenEmbeddingModel)
    embedding_model._model = cast(Any, model)
    embedding_model._batch_size = 8
    return embedding_model


@pytest.mark.asyncio
async def test_embed_query_uses_query_prompt() -> None:
    model = StubModel()

    result = await make_embedding_model(model).embed_query(["question"])

    assert len(result[0]) == 1024
    assert model.kwargs is not None
    assert model.kwargs["prompt_name"] == "query"


@pytest.mark.asyncio
async def test_embed_documents_does_not_use_prompt() -> None:
    model = StubModel()

    await make_embedding_model(model).embed(["question"])

    assert model.kwargs is not None
    assert "prompt_name" not in model.kwargs
