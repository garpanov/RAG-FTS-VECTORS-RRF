import asyncio
from typing import Any, cast


class QwenReranker:
    def __init__(
        self,
        model_name: str,
        device: str,
        batch_size: int,
    ) -> None:
        from sentence_transformers import CrossEncoder

        self._model = CrossEncoder(model_name, device=device)
        self._batch_size = batch_size

    async def rerank(self, question: str, chunks: list[str]) -> list[float]:
        if not chunks:
            return []
        return await asyncio.to_thread(self._rerank_sync, question, chunks)

    def _rerank_sync(self, question: str, chunks: list[str]) -> list[float]:
        scores = cast(
            Any,
            self._model.predict(
                [(question, chunk) for chunk in chunks],
                batch_size=self._batch_size,
                show_progress_bar=False,
            ),
        )
        return [float(score) for score in scores.tolist()]
