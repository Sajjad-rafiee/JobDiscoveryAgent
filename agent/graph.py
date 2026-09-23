from langgraph.graph import END, START, StateGraph

from agent.model import get_chat_model
from agent.state import AgentState


def chat(state: AgentState) -> dict:
    model = get_chat_model()
    response = model.invoke(state["messages"])
    return {"messages": [response]}


def build_graph():
    builder = StateGraph(AgentState)
    builder.add_node("chat", chat)
    builder.add_edge(START, "chat")
    builder.add_edge("chat", END)
    return builder.compile()


graph = build_graph()
