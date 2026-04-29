from __future__ import annotations

from ..state import QueryState


RAG_RESPONSE_PROMPT = """You are a helpful assistant. Answer the question based on the provided context.

Context:
{context_data}

Response Type: {response_type}

{user_prompt}
"""


async def generate_answer(state: QueryState) -> dict:
    ctx = _get_context()
    context = state.get("context", "")
    if not context.strip():
        return {"answer": "I don't have enough information to answer this question."}

    param = state["param"]
    user_prompt_text = f"\n\nAdditional instructions: {param.get('user_prompt', '')}" if param.get("user_prompt") else ""
    sys_prompt = RAG_RESPONSE_PROMPT.format(
        context_data=context,
        response_type=param.get("response_type", "Multiple Paragraphs"),
        user_prompt=user_prompt_text,
    )

    messages = []
    messages.append(("system", sys_prompt))

    history = param.get("conversation_history", [])
    for msg in history:
        role = msg.get("role", "user")
        messages.append((role, msg.get("content", "")))

    messages.append(("human", state["question"]))
    result = await ctx["llm"].ainvoke(messages)

    answer = result.content
    answer = answer.replace(sys_prompt, "").replace(state["question"], "").strip()

    return {"answer": answer}


def _get_context():
    import app.agent.graph as g
    return g._STORAGE_CTX
