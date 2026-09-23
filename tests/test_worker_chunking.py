import pytest

from worker.chunking import MarkdownChunker


class WordTokenizer:
    def __init__(self) -> None:
        self._token_ids: dict[str, int] = {}
        self._tokens: dict[int, str] = {}

    def encode(self, text: str, *, add_special_tokens: bool = False) -> list[int]:
        result: list[int] = []
        for token in text.split():
            if token not in self._token_ids:
                token_id = len(self._token_ids)
                self._token_ids[token] = token_id
                self._tokens[token_id] = token
            result.append(self._token_ids[token])
        return result

    def decode(self, token_ids: list[int], *, skip_special_tokens: bool = True) -> str:
        return " ".join(self._tokens[token_id] for token_id in token_ids)


def test_chunker_preserves_heading_hierarchy() -> None:
    chunker = MarkdownChunker(WordTokenizer())

    chunks = chunker.split(
        "# Payments\n## Refunds\n### Conditions\nRefunds are available.\n"
        "### Timing\nRefunds take five days."
    )

    assert chunks == [
        "# Payments\n## Refunds\n### Conditions\nRefunds are available.",
        "# Payments\n## Refunds\n### Timing\nRefunds take five days.",
    ]


def test_chunker_limits_chunks_and_overlaps_long_answers() -> None:
    tokenizer = WordTokenizer()
    chunker = MarkdownChunker(tokenizer, max_tokens=300, overlap_tokens=30)
    answer = " ".join(f"word-{index}" for index in range(400))

    chunks = chunker.split(f"# Theme\n## Question\n### Answer\n{answer}")

    assert len(chunks) == 2
    assert all(len(tokenizer.encode(chunk)) <= 300 for chunk in chunks)
    first_body = chunks[0].splitlines()[-1].split()
    second_body = chunks[1].splitlines()[-1].split()
    assert first_body[-30:] == second_body[:30]
    assert all(chunk.startswith("# Theme\n## Question\n### Answer\n") for chunk in chunks)


def test_chunker_rejects_invalid_window_configuration() -> None:
    with pytest.raises(
        ValueError,
        match="overlap_tokens must be between 0 and max_tokens",
    ):
        MarkdownChunker(WordTokenizer(), max_tokens=30, overlap_tokens=30)
