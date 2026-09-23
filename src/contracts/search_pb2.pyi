from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class SearchChunksRequest(_message.Message):
    __slots__ = ("question", "limit")
    QUESTION_FIELD_NUMBER: _ClassVar[int]
    LIMIT_FIELD_NUMBER: _ClassVar[int]
    question: str
    limit: int
    def __init__(self, question: _Optional[str] = ..., limit: _Optional[int] = ...) -> None: ...

class Chunk(_message.Message):
    __slots__ = ("document_id", "document_number", "chunk_number", "content", "distance")
    DOCUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    DOCUMENT_NUMBER_FIELD_NUMBER: _ClassVar[int]
    CHUNK_NUMBER_FIELD_NUMBER: _ClassVar[int]
    CONTENT_FIELD_NUMBER: _ClassVar[int]
    DISTANCE_FIELD_NUMBER: _ClassVar[int]
    document_id: int
    document_number: str
    chunk_number: int
    content: str
    distance: float
    def __init__(self, document_id: _Optional[int] = ..., document_number: _Optional[str] = ..., chunk_number: _Optional[int] = ..., content: _Optional[str] = ..., distance: _Optional[float] = ...) -> None: ...

class SearchChunksResponse(_message.Message):
    __slots__ = ("chunks",)
    CHUNKS_FIELD_NUMBER: _ClassVar[int]
    chunks: _containers.RepeatedCompositeFieldContainer[Chunk]
    def __init__(self, chunks: _Optional[_Iterable[_Union[Chunk, _Mapping]]] = ...) -> None: ...

class RerankChunksRequest(_message.Message):
    __slots__ = ("question",)
    QUESTION_FIELD_NUMBER: _ClassVar[int]
    question: str
    def __init__(self, question: _Optional[str] = ...) -> None: ...

class RerankedChunk(_message.Message):
    __slots__ = ("document_id", "document_number", "chunk_number", "content", "distance", "reranker_score")
    DOCUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    DOCUMENT_NUMBER_FIELD_NUMBER: _ClassVar[int]
    CHUNK_NUMBER_FIELD_NUMBER: _ClassVar[int]
    CONTENT_FIELD_NUMBER: _ClassVar[int]
    DISTANCE_FIELD_NUMBER: _ClassVar[int]
    RERANKER_SCORE_FIELD_NUMBER: _ClassVar[int]
    document_id: int
    document_number: str
    chunk_number: int
    content: str
    distance: float
    reranker_score: float
    def __init__(self, document_id: _Optional[int] = ..., document_number: _Optional[str] = ..., chunk_number: _Optional[int] = ..., content: _Optional[str] = ..., distance: _Optional[float] = ..., reranker_score: _Optional[float] = ...) -> None: ...

class RerankChunksResponse(_message.Message):
    __slots__ = ("chunks",)
    CHUNKS_FIELD_NUMBER: _ClassVar[int]
    chunks: _containers.RepeatedCompositeFieldContainer[RerankedChunk]
    def __init__(self, chunks: _Optional[_Iterable[_Union[RerankedChunk, _Mapping]]] = ...) -> None: ...
