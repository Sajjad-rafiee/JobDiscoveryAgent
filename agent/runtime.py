from collections.abc import Sequence
from typing import Any

from langchain_core.messages import MessageLikeRepresentation

from agent.graph import graph


def invoke_agent(messages: Sequence[MessageLikeRepresentation]) -> dict[str, Any]:
    """Run the agent on a conversation and return the final graph state.

    `messages` is the conversation so far, in any form LangChain accepts
    (message objects or dicts such as {"role": "user", "content": "..."}).
    The returned state's "messages" holds the full conversation, ending with
    the agent's reply.
    """
    if isinstance(messages, str):
        raise TypeError("messages must be a sequence of messages, not a string")
    return graph.invoke({"messages": list(messages)})
