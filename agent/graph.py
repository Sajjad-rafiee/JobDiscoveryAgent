from langgraph.graph import START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from agent.model import get_model_info, get_tool_enabled_chat_model
from agent.state import AgentState
from prompts.agent import build_agent_prompt
from tools import TOOLS
from utils.telemetry import get_tracer


def chat(state: AgentState) -> dict:
    prompt = build_agent_prompt().invoke({"messages": state["messages"]})
    model = get_tool_enabled_chat_model()

    with get_tracer().start_as_current_span("chat") as span:
        span.set_attribute("gen_ai.operation.name", "chat")
        if span.is_recording():
            # Only resolve provider/model (a settings load) when the span is
            # actually going to be exported — keeps chat() free of config
            # requirements when tracing is off, e.g. under test fakes.
            provider, model_name = get_model_info()
            span.set_attribute("gen_ai.provider.name", provider)
            span.set_attribute("gen_ai.request.model", model_name)
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
