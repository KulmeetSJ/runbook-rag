"""Retrieval modes: vector (cosine), lexical (PostgreSQL full-text), hybrid (reciprocal rank fusion).

Lexical is PostgreSQL full-text search ranked with ts_rank_cd, not true BM25: no IDF term and its own
length normalisation. Questions are OR-ed term by term (plainto/websearch_to_tsquery AND every term, so
a natural-language question rarely matches anything). Titles and section headings are weighted higher.
"""
from dataclasses import dataclass

from .embeddings import EMBEDDERS

RRF_K = 60          # standard RRF constant (Cormack et al., 2009)
CANDIDATES = 50     # per-mode candidates fed into fusion


@dataclass
class Hit:
    chunk_id: str
    doc_id: str
    title: str
    section: str
    content: str
    score: float
    poisoned: bool = False


COLS = "chunk_id, doc_id, title, section, content, poisoned"


def _hits(rows) -> list[Hit]:
    return [Hit(r[0], r[1], r[2], r[3], r[4], float(r[6]), r[5]) for r in rows]


def vector(conn, index_name: str, query: str, k: int) -> list[Hit]:
    embedder = EMBEDDERS[index_name.split(":")[1]]
    q = embedder.query(query)
    rows = conn.execute(
        f"SELECT {COLS}, 1 - (embedding <=> %s) AS score FROM chunks WHERE index_name = %s"
        " ORDER BY embedding <=> %s LIMIT %s", (q, index_name, q, k)).fetchall()
    return _hits(rows)


def lexical(conn, index_name: str, query: str, k: int) -> list[Hit]:
    rows = conn.execute(
        f"""WITH q AS (
              SELECT to_tsquery('simple', coalesce(nullif(array_to_string(array(
                  SELECT quote_literal(lexeme) FROM unnest(tsvector_to_array(to_tsvector('english', %s))) AS lexeme
              ), ' | '), ''), 'xxnomatchxx')) AS tsq)
            SELECT {COLS}, ts_rank_cd(tsv, q.tsq, 1) AS score FROM chunks, q
            WHERE index_name = %s AND tsv @@ q.tsq ORDER BY score DESC, chunk_id LIMIT %s""",
        (query, index_name, k)).fetchall()
    return _hits(rows)


def hybrid(conn, index_name: str, query: str, k: int) -> list[Hit]:
    fused: dict[str, Hit] = {}
    scores: dict[str, float] = {}
    for ranked in (vector(conn, index_name, query, CANDIDATES), lexical(conn, index_name, query, CANDIDATES)):
        for rank, hit in enumerate(ranked, start=1):
            fused.setdefault(hit.chunk_id, hit)
            scores[hit.chunk_id] = scores.get(hit.chunk_id, 0.0) + 1.0 / (RRF_K + rank)
    order = sorted(scores, key=lambda c: (-scores[c], c))[:k]
    out = []
    for cid in order:
        h = fused[cid]
        h.score = scores[cid]
        out.append(h)
    return out


MODES = {"vector": vector, "lexical": lexical, "hybrid": hybrid}


def search(conn, index_name: str, query: str, k: int = 5, mode: str = "hybrid") -> list[Hit]:
    return MODES[mode](conn, index_name, query, k)
