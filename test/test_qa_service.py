from types import SimpleNamespace
from unittest.mock import MagicMock

from app.domain.schemas import Citation
from app.services.qa_service import QAService


class DummyChat:
    def build_chat_context(self, question):
        return f"context for: {question}"

    def chat_answer(self, question, context):
        return f"answer for: {question}"

    def compress_history(self, text):
        return text

    def answer_stream(self, question, context):
        yield "token1 "
        yield "token2"

    def chat_answer_stream(self, question, context):
        yield "chat_token1"
        yield "chat_token2"

    def detect_malicious_input(self, question):
        return []


class DummyDB:
    def __init__(self):
        self.added = []
        self.committed = False

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.committed = True

    def query(self, *args, **kwargs):
        class DummyQuery:
            def filter(self, *a, **kw):
                return self
            def first(self):
                return None
            def count(self):
                return 0
        return DummyQuery()


def test_qa_service_non_retrieval_mode():
    service = QAService.__new__(QAService)
    service.db = DummyDB()
    service.settings = SimpleNamespace(
        chat_provider="test",
        chat_model="test-model",
        embedding_model="emb-model",
        workflow_block_malicious_input=False,
    )
    service.chat = DummyChat()

    class DummyMemory:
        def get_or_create_session(self, session_id=None):
            return SimpleNamespace(id=1)
        def get_messages(self, session_id):
            return []
        def add_message(self, *args, **kwargs):
            pass
    service.memory = DummyMemory()

    resp = service.ask("你好", 5, use_retrieval=False)
    assert resp.answer == "answer for: 你好"
    assert resp.intent == "chat"
    assert len(resp.citations) == 0
    assert resp.session_id == 1
    assert service.db.committed is True


def test_qa_service_malicious_input_blocked():
    class BlockingChat(DummyChat):
        def detect_malicious_input(self, question):
            return ["malicious_llm:hack_attempt"]
    service = QAService.__new__(QAService)
    service.db = DummyDB()
    service.settings = SimpleNamespace(
        chat_provider="test",
        chat_model="test-model",
        embedding_model="emb-model",
        workflow_block_malicious_input=True,
    )
    service.chat = BlockingChat()

    class DummyMemory:
        def get_or_create_session(self, session_id=None):
            return SimpleNamespace(id=1)
        def get_messages(self, session_id):
            return []
        def add_message(self, *args, **kwargs):
            pass
    service.memory = DummyMemory()

    result = service.ask_stream("恶意输入", 5)
    answer = "".join(result["stream"])
    assert "恶意输入" in answer
    assert result["evaluation"]["blocked"] is True
