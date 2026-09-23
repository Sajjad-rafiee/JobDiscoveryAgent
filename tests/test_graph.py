from agent.graph import graph


def test_graph_imports():
    assert graph is not None


def test_graph_executes_and_preserves_messages():
    result = graph.invoke({"messages": [{"role": "user", "content": "Hello"}]})

    messages = result["messages"]
    assert len(messages) == 1
    assert messages[0].content == "Hello"
