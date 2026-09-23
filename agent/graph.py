from langgraph.graph import END, START, StateGraph

from agent.state import AgentState


def chat(state: AgentState) -> dict:
    return {}


def build_graph():
    builder = StateGraph(AgentState)
    builder.add_node("chat", chat)
    builder.add_edge(START, "chat")
    builder.add_edge("chat", END)
    return builder.compile()


graph = build_graph()
