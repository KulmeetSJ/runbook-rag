"""pgvector store. One table holds several indexes (chunking strategy x embedder), keyed by index_name.

The corpus is ~100 chunks per index, so queries use an exact scan; an HNSW index would need a fixed
vector dimension per column and only pays off at tens of thousands of rows.
"""
import psycopg
from pgvector.psycopg import register_vector

from .chunking import Chunk
from .config import db_url

SCHEMA = """
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE IF NOT EXISTS chunks (
    index_name text NOT NULL,
    chunk_id   text NOT NULL,
    doc_id     text NOT NULL,
    title      text NOT NULL,
    section    text NOT NULL,
    version    int  NOT NULL,
    poisoned   boolean NOT NULL DEFAULT false,
    content    text NOT NULL,
    embedding  vector NOT NULL,
    tsv tsvector GENERATED ALWAYS AS
        (setweight(to_tsvector('english', title || ' ' || section), 'A') || to_tsvector('english', content)) STORED,
    PRIMARY KEY (index_name, chunk_id)
);
CREATE INDEX IF NOT EXISTS chunks_tsv ON chunks USING gin (tsv);
"""


def connect() -> psycopg.Connection:
    conn = psycopg.connect(db_url(), autocommit=True)
    conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
    register_vector(conn)
    return conn


def init(conn: psycopg.Connection) -> None:
    conn.execute(SCHEMA)


def replace_index(conn, index_name: str, rows: list[tuple[Chunk, int, bool, object]]) -> None:
    """Atomically replace one index: rows are (chunk, version, poisoned, embedding)."""
    with conn.transaction():
        conn.execute("DELETE FROM chunks WHERE index_name = %s", (index_name,))
        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO chunks (index_name, chunk_id, doc_id, title, section, version, poisoned, content, embedding)"
                " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                [(index_name, c.chunk_id, c.doc_id, c.title, c.section, v, p, c.text, e) for c, v, p, e in rows],
            )


def indexes(conn) -> list[tuple[str, int, int]]:
    return conn.execute(
        "SELECT index_name, count(*), count(DISTINCT doc_id) FROM chunks GROUP BY 1 ORDER BY 1").fetchall()
