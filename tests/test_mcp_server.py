"""End-to-end over a real stdio MCP session (needs the database; skipped without it)."""
import asyncio
import json
import os
import sys

import pytest

pytest.importorskip("mcp")
from mcp import ClientSession, StdioServerParameters  # noqa: E402
from mcp.client.stdio import stdio_client  # noqa: E402

from rag import store  # noqa: E402


def _db_up() -> bool:
    try:
        store.connect().close()
        return True
    except BaseException:
        return False


pytestmark = pytest.mark.skipif(not _db_up(), reason="database not running")


async def _session_calls():
    params = StdioServerParameters(command=sys.executable, args=["-m", "rag.mcp_server"], env=dict(os.environ))
    async with stdio_client(params) as (r, w), ClientSession(r, w) as s:
        await s.initialize()
        tools = {t.name: t for t in (await s.list_tools()).tools}
        search = await s.call_tool("search_runbooks", {"query": "reset consumer offsets to fix lag", "k": 5})
        good = await s.call_tool("get_runbook", {"doc_id": "pf-scaling"})
        bad = await s.call_tool("get_runbook", {"doc_id": "untrusted-kafka-tuning"})
        return tools, search, good, bad


def _payload(result):
    if result.structured_content is not None:
        sc = result.structured_content
        return sc.get("result", sc)
    return json.loads(result.content[0].text)


def test_mcp_tools_are_read_only_and_quarantine_unreviewed_docs():
    tools, search, good, bad = asyncio.run(_session_calls())
    assert set(tools) == {"search_runbooks", "get_runbook", "ask_runbooks"}
    assert all(t.annotations.read_only_hint for t in tools.values())
    hits = _payload(search)
    assert hits and not any(h["doc_id"].startswith("untrusted-") for h in hits)
    assert "6 partitions" in _payload(good)["text"]
    assert "error" in _payload(bad)
