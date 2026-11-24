"""Ingest: load -> redact -> chunk -> embed -> upsert. Redaction happens before anything is embedded or stored."""
import time
from dataclasses import dataclass, field

from . import chunking, corpus, redact, store
from .embeddings import EMBEDDERS


@dataclass
class Report:
    index_name: str
    docs: int = 0
    chunks: int = 0
    redacted: dict[str, int] = field(default_factory=dict)
    seconds: float = 0.0


def index_name(strategy: str, embedder: str) -> str:
    return f"{strategy}:{embedder}"


def run(conn, strategy: str, embedder: str) -> Report:
    t0 = time.perf_counter()
    rep = Report(index_name(strategy, embedder))
    chunker, emb = chunking.STRATEGIES[strategy], EMBEDDERS[embedder]
    rows = []
    for doc in corpus.load():
        body, counts = redact.redact(doc.body)
        for k, v in counts.items():
            rep.redacted[k] = rep.redacted.get(k, 0) + v
        chunks = chunker(doc, body)
        vectors = emb.passages([c.embed_text for c in chunks])
        rows += [(c, doc.version, doc.poisoned, v) for c, v in zip(chunks, vectors)]
        rep.docs += 1
    store.init(conn)
    store.replace_index(conn, rep.index_name, rows)
    rep.chunks, rep.seconds = len(rows), time.perf_counter() - t0
    return rep
