from __future__ import annotations

import json_repair

from ..state import QueryState


KEYWORDS_EXTRACTION_PROMPT = """Analyze the following query and extract two levels of keywords:

High-level keywords: broad topics/concepts (2-5 keywords)
Low-level keywords: specific details/entities (3-8 keywords)

Query: {query}

Output as JSON:
{{
  "high_level_keywords": ["keyword1", "keyword2"],
  "low_level_keywords": ["keyword1", "keyword2", "keyword3"]
}}"""


async def extract_keywords_node(state: QueryState) -> dict:
    ctx = _get_context()
    param = state["param"]

    if param.get("hl_keywords") or param.get("ll_keywords"):
        return {
            "hl_keywords": param.get("hl_keywords", []),
            "ll_keywords": param.get("ll_keywords", []),
        }

    prompt = KEYWORDS_EXTRACTION_PROMPT.format(query=state["question"])
    messages = [("human", prompt)]
    result = await ctx["llm"].ainvoke(messages)

    try:
        content = result.content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1]
            content = content.rsplit("```", 1)[0]
        data = json_repair.loads(content)
        hl = data.get("high_level_keywords", [])
        ll = data.get("low_level_keywords", [])
        if isinstance(hl, list) and isinstance(ll, list):
            return {"hl_keywords": hl, "ll_keywords": ll}
    except Exception:
        pass

    return {"hl_keywords": [], "ll_keywords": [state["question"]]}


def route_by_mode(state: QueryState) -> list[str]:
    mode = state["param"].get("mode", "hybrid")
    if mode == "local":
        return ["local_search"]
    elif mode == "global":
        return ["global_search"]
    elif mode == "naive":
        return ["naive_search"]
    else:
        return ["local_search", "global_search", "naive_search"]


def _get_context():
    import app.agent.graph as g
    return g._STORAGE_CTX
