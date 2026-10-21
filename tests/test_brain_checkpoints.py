import asyncio
import sys
from types import SimpleNamespace
from uuid import uuid4

import pytest
from langgraph.graph import END, START, StateGraph

from app.services.brain.checkpoints import checkpoint_saver, postgres_uri, setup_postgres_checkpoints


def test_postgres_uri_preserves_escaped_credentials():
    from sqlalchemy.engine import make_url

    url = make_url("postgresql+psycopg://aria:a%40b%2Fc@localhost/aria?sslmode=require")
    converted = make_url(postgres_uri(url))
    assert converted.drivername == "postgresql"
    assert converted.password == "a@b/c"
    assert converted.query["sslmode"] == "require"


def test_postgres_graph_resumes_after_connection_reopens(engine):
    if engine.dialect.name != "postgresql":
        pytest.skip("Requires real PostgreSQL; covered by backend-postgres CI")
    # Repeated setup must be harmless across backend restarts.
    setup_postgres_checkpoints(engine.url)
    setup_postgres_checkpoints(engine.url)
    db = SimpleNamespace(get_bind=lambda: engine)
    thread = f"checkpoint-test:{uuid4()}"
    config = {"configurable": {"thread_id": thread}}
    calls = []

    async def verify():
        builder = StateGraph(int)

        async def increment(value):
            calls.append(value)
            return value + 1

        builder.add_node("execute", increment)
        builder.add_edge(START, "execute")
        builder.add_edge("execute", END)
        async with checkpoint_saver(db) as saver:
            graph = builder.compile(checkpointer=saver, interrupt_before=["execute"])
            await graph.ainvoke(1, config)
            assert (await graph.aget_state(config)).next == ("execute",)
            assert calls == []
        # A fresh saver/connection stands in for a different backend worker.
        async with checkpoint_saver(db) as saver:
            try:
                graph = builder.compile(checkpointer=saver, interrupt_before=["execute"])
                assert await graph.ainvoke(None, config) == 2
                assert (await graph.aget_state(config)).next == ()
                assert calls == [1]
            finally:
                await saver.adelete_thread(thread)

    # psycopg async requires a selector loop on Windows; Linux uses its default.
    if sys.platform == "win32":
        with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
            runner.run(verify())
    else:
        asyncio.run(verify())
