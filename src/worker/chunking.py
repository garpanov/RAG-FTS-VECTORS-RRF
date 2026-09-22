import re
from dataclasses import dataclass
from typing import Protocol

HEADING_PATTERN = re.compile(r"^(#{1,3})\s+(.+?)\s*$")


class Tokenizer(Protocol):
    def encode(self, text: str, *, add_special_tokens: bool = False) -> list[int]: ...

    def decode(self, token_ids: list[int], *, skip_special_tokens: bool = True) -> str: ...


@dataclass(frozen=True)
class MarkdownSection:
    headings: tuple[str, ...]
    body: str

    @property
    def prefix(self) -> str:
        return "\n".join(self.headings)

    @property
    def content(self) -> str:
        return "\n".join(part for part in (self.prefix, self.body) if part)


class MarkdownChunker:
    def __init__(
        self,
        tokenizer: Tokenizer,
        max_tokens: int = 300,
        overlap_tokens: int = 30,
    ) -> None:
        if max_tokens <= 0:
            raise ValueError("max_tokens must be positive")
        if overlap_tokens < 0 or overlap_tokens >= max_tokens:
            raise ValueError("overlap_tokens must be between 0 and max_tokens")

        self._tokenizer = tokenizer
        self._max_tokens = max_tokens
        self._overlap_tokens = overlap_tokens

    def split(self, document: str) -> list[str]:
        chunks: list[str] = []
        for section in self._parse_sections(document):
            chunks.extend(self._split_section(section))
        return chunks

    def _parse_sections(self, document: str) -> list[MarkdownSection]:
        headings: list[str] = []
        body_lines: list[str] = []
        sections: list[MarkdownSection] = []

        def flush() -> None:
            body = "\n".join(body_lines).strip()
            if body or (headings and headings[-1].startswith("### ")):
                sections.append(MarkdownSection(tuple(headings), body))
            body_lines.clear()

        for line in document.splitlines():
            match = HEADING_PATTERN.match(line)
            if match is None:
                body_lines.append(line)
                continue

            flush()
            level = len(match.group(1))
            heading = f"{'#' * level} {match.group(2)}"
            headings[level - 1 :] = [heading]

        flush()
        return sections

    def _split_section(self, section: MarkdownSection) -> list[str]:
        content_ids = self._tokenizer.encode(section.content, add_special_tokens=False)
        if len(content_ids) <= self._max_tokens:
            return [section.content] if section.content else []

        prefix = section.prefix
        prefix_with_separator = f"{prefix}\n" if prefix else ""
        prefix_ids = self._tokenizer.encode(prefix_with_separator, add_special_tokens=False)
        body_ids = self._tokenizer.encode(section.body, add_special_tokens=False)
        body_capacity = self._max_tokens - len(prefix_ids)

        if not body_ids or body_capacity <= self._overlap_tokens:
            return self._split_token_window(content_ids)

        step = body_capacity - self._overlap_tokens
        chunks: list[str] = []
        for start in range(0, len(body_ids), step):
            window = body_ids[start : start + body_capacity]
            decoded_body = self._tokenizer.decode(window, skip_special_tokens=True).strip()
            chunks.append(f"{prefix_with_separator}{decoded_body}".strip())
            if start + body_capacity >= len(body_ids):
                break
        return chunks

    def _split_token_window(self, token_ids: list[int]) -> list[str]:
        step = self._max_tokens - self._overlap_tokens
        chunks: list[str] = []
        for start in range(0, len(token_ids), step):
            window = token_ids[start : start + self._max_tokens]
            chunks.append(self._tokenizer.decode(window, skip_special_tokens=True).strip())
            if start + self._max_tokens >= len(token_ids):
                break
        return chunks
