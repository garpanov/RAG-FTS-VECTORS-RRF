import asyncio
from typing import Any, cast

from worker.chunking import Tokenizer


class QwenEmbeddingModel:
    def __init__(
        self,
        model_name: str,
        device: str,
        batch_size: int,
    ) -> None:
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(model_name, device=device)
        if self._model.get_sentence_embedding_dimension() != 1024:
            raise ValueError("Embedding model must produce 1024-dimensional vectors")
        self._tokenizer = cast(Tokenizer, self._model.tokenizer)
        self._batch_size = batch_size

    def encode(self, text: str, *, add_special_tokens: bool = False) -> list[int]:
        return self._tokenizer.encode(text, add_special_tokens=add_special_tokens)

    def decode(self, token_ids: list[int], *, skip_special_tokens: bool = True) -> str:
        return self._tokenizer.decode(token_ids, skip_special_tokens=skip_special_tokens)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return await asyncio.to_thread(self._embed_sync, texts)

    async def embed_query(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return await asyncio.to_thread(self._embed_sync, texts, prompt_name="query")

    def _embed_sync(
        self,
        texts: list[str],
        *,
        prompt_name: str | None = None,
    ) -> list[list[float]]:
        encode_kwargs: dict[str, Any] = {
            "batch_size": self._batch_size,
            "convert_to_numpy": True,
            "normalize_embeddings": True,
            "show_progress_bar": False,
        }
        if prompt_name is not None:
            encode_kwargs["prompt_name"] = prompt_name

        embeddings = cast(
            Any,
            self._model.encode(texts, **encode_kwargs),
        )
        return cast(list[list[float]], embeddings.tolist())
