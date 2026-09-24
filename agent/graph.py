from langgraph.graph import START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from agent.model import get_tool_enabled_chat_model
from agent.state import AgentState
from prompts.agent import build_agent_prompt
from tools import TOOLS


def chat(state: AgentState) -> dict:
    prompt = build_agent_prompt().invoke({"messages": state["messages"]})
    model = get_tool_enabled_chat_model()
    response = model.invoke(prompt.to_messages())
    return {"messages": [response]}


def build_graph():
    builder = StateGraph(AgentState)
    builder.add_node("chat", chat)
    builder.add_node("tools", ToolNode(TOOLS))
    builder.add_edge(START, "chat")
    builder.add_conditional_edges("chat", tools_condition)
    builder.add_edge("tools", "chat")
    return builder.compile()


graph = build_graph()
