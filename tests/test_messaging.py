import pytest
from pydantic import ValidationError

from app.messaging import DocumentChunkingTask


def test_document_chunking_task_serializes_document_id() -> None:
    task = DocumentChunkingTask(document_id=42)

    assert task.model_dump_json() == '{"document_id":42}'


def test_document_chunking_task_rejects_non_positive_id() -> None:
    with pytest.raises(ValidationError):
        DocumentChunkingTask(document_id=0)
