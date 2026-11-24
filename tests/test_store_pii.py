"""Integration: no seeded PII string may exist anywhere in the vector store. Needs `docker compose up`."""
from pathlib import Path

import pytest

SEEDS = [l for l in (Path(__file__).parent / "fixtures/seeded_pii.txt").read_text().splitlines()
         if l and not l.startswith("#")]


@pytest.fixture(scope="module")
def conn():
    from rag import store
    try:
        return store.connect()
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"database not available: {e}")


def test_store_has_indexes(conn):
    assert conn.execute("SELECT count(*) FROM chunks").fetchone()[0] > 0


def test_no_seeded_pii_in_stored_chunks(conn):
    leaks = []
    for s in SEEDS:
        rows = conn.execute("SELECT index_name, chunk_id FROM chunks WHERE content ILIKE %s OR title ILIKE %s",
                            (f"%{s}%", f"%{s}%")).fetchall()
        leaks += [(s, *r) for r in rows]
    assert not leaks
