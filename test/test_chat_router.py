from types import SimpleNamespace

from app.agent.chat_router import ChatRouter


def _build_router_with_mocked_response(content: str):
    router = ChatRouter.__new__(ChatRouter)
    router.settings = SimpleNamespace(chat_model="test-model", workflow_intent_low_confidence_threshold=0.65)
    router.intent_prompt = object()
    router._invoke_text = lambda _prompt, _payload, temperature: content
    return router


def test_classify_intent_returns_chat_when_model_says_chat():
    router = _build_router_with_mocked_response('{"intent":"chat"}')
    assert router.classify_intent("你好") == "chat"


def test_classify_intent_returns_qa_when_model_says_qa():
    router = _build_router_with_mocked_response('{"intent":"qa"}')
    assert router.classify_intent("RAG 的定义是什么？") == "qa"


def test_classify_intent_fallbacks_to_chat_on_invalid_json():
    router = _build_router_with_mocked_response("not json")
    assert router.classify_intent("随便聊聊") == "chat"


def test_classify_intent_returns_qa_on_invalid_intent_value():
    router = _build_router_with_mocked_response('{"intent":"unknown","confidence":0.9,"reason":"bad-value"}')
    assert router.classify_intent("RAG 原理是什么") == "qa"


def test_classify_intent_uses_rule_fallback_on_low_confidence():
    router = _build_router_with_mocked_response('{"intent":"chat","confidence":0.2,"reason":"uncertain"}')
    assert router.classify_intent("什么是向量数据库？") == "qa"


def test_classify_intent_short_circuits_greeting_to_chat():
    router = _build_router_with_mocked_response('{"intent":"qa","confidence":0.99,"reason":"wrong"}')
    assert router.classify_intent("你好") == "chat"
