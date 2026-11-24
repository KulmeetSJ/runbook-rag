"""Two chunking strategies, so they can be compared in the evals.

- fixed:   sliding windows of N tokens (bge tokenizer) with overlap, blind to document structure.
- heading: one chunk per markdown section (## / ###), with the doc title and section path as a header.
           Fenced code blocks are never split. Sections longer than max_tokens are split on paragraphs;
           sections shorter than min_tokens are merged into the previous chunk.

Chunk IDs are stable across runs: "<doc_id>#<n>" for fixed, "<doc_id>#<section-slug>" for heading.
Evals label relevance at document level, so the same golden set scores both strategies.
"""
import re
from dataclasses import dataclass
from functools import lru_cache

from tokenizers import Tokenizer

from .corpus import Doc


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    doc_id: str
    title: str
    section: str
    text: str          # what is stored and shown (redacted)
    embed_text: str    # what is embedded: header + text


@lru_cache(maxsize=1)
def tokenizer() -> Tokenizer:
    return Tokenizer.from_pretrained("BAAI/bge-small-en-v1.5")


def n_tokens(text: str) -> int:
    return len(tokenizer().encode(text, add_special_tokens=False).ids)


def fixed(doc: Doc, body: str, size: int = 512, overlap: int = 64) -> list[Chunk]:
    enc = tokenizer().encode(body, add_special_tokens=False)
    chunks, start, n = [], 0, 0
    while start < len(enc.ids):
        end = min(start + size, len(enc.ids))
        text = body[enc.offsets[start][0]:enc.offsets[end - 1][1]]
        chunks.append(Chunk(f"{doc.doc_id}#{n}", doc.doc_id, doc.title, "", text, f"{doc.title}\n{text}"))
        if end == len(enc.ids):
            break
        start, n = end - overlap, n + 1
    return chunks


HEADING = re.compile(r"^(#{1,3}) +(.+?)\s*$")


def _sections(body: str) -> list[tuple[str, str]]:
    """Split markdown into (section path, text) on # / ## / ### headings outside code fences."""
    out, path, buf, in_fence = [], [], [], False
    def flush():
        text = "\n".join(buf).strip()
        if text:
            out.append((" > ".join(path[1:]) or "Overview", text))
    for line in body.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        m = None if in_fence else HEADING.match(line)
        if m:
            flush()
            buf = []
            level = len(m.group(1))
            path = path[:level - 1] + [m.group(2)]
        else:
            buf.append(line)
    flush()
    return out


def _split_long(text: str, max_tokens: int) -> list[str]:
    parts, cur = [], ""
    for para in re.split(r"\n\s*\n", text):
        cand = f"{cur}\n\n{para}" if cur else para
        if cur and n_tokens(cand) > max_tokens:
            parts.append(cur)
            cur = para
        else:
            cur = cand
    return parts + [cur] if cur else parts


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-") or "overview"


def heading(doc: Doc, body: str, max_tokens: int = 400, min_tokens: int = 40) -> list[Chunk]:
    pieces: list[list[str]] = []   # [section, text]
    for section, text in _sections(body):
        for part in _split_long(text, max_tokens):
            if pieces and n_tokens(part) < min_tokens:
                pieces[-1][1] += f"\n\n{section}:\n{part}" if pieces[-1][0] != section else f"\n\n{part}"
            else:
                pieces.append([section, part])
    chunks, seen = [], {}
    for section, text in pieces:
        base = slug(section)
        seen[base] = seen.get(base, 0) + 1
        cid = f"{doc.doc_id}#{base}" + (f"-{seen[base]}" if seen[base] > 1 else "")
        header = f"{doc.title} > {section}"
        chunks.append(Chunk(cid, doc.doc_id, doc.title, section, text, f"{header}\n{text}"))
    return chunks


STRATEGIES = {
    "fixed512": lambda d, b: fixed(d, b, 512, 64),
    "fixed128": lambda d, b: fixed(d, b, 128, 16),
    "heading": heading,
}
