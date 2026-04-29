import json
import re
from collections.abc import Iterator

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI

from app.core.settings import get_settings
from app.agent.prompts import (
    ANSWER_PROMPT,
    CHAT_ANSWER_PROMPT,
    CHAT_CONTEXT_PROMPT,
    CHAT_EVAL_PROMPT,
    COMPRESS_PROMPT,
    INTENT_PROMPT,
    QA_EVAL_PROMPT,
    REWRITE_PROMPT,
    SECURITY_PROMPT,
)


class ChatRouter:
    def __init__(self) -> None:
        settings = get_settings()
        self.settings = settings
        self.client = ChatOpenAI(
            model=settings.chat_model,
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )
        self.output_parser = StrOutputParser()
        self.answer_prompt = ANSWER_PROMPT
        self.chat_answer_prompt = CHAT_ANSWER_PROMPT
        self.intent_prompt = INTENT_PROMPT
        self.security_prompt = SECURITY_PROMPT
        self.chat_context_prompt = CHAT_CONTEXT_PROMPT
        self.compress_prompt = COMPRESS_PROMPT
        self.rewrite_prompt = REWRITE_PROMPT
        self.chat_eval_prompt = CHAT_EVAL_PROMPT
        self.qa_eval_prompt = QA_EVAL_PROMPT

    def _build_chain(self, prompt, temperature: float) -> Runnable:
        return prompt | self.client.bind(temperature=temperature) | self.output_parser

    def _invoke_text(self, prompt: ChatPromptTemplate, payload: dict, temperature: float) -> str:
        return self._build_chain(prompt, temperature).invoke(payload)

    def _stream_text(self, prompt: ChatPromptTemplate, payload: dict, temperature: float) -> Iterator[str]:
        for chunk in self._build_chain(prompt, temperature).stream(payload):
            if chunk:
                yield chunk

    def answer(self, question: str, context: str) -> str:
        content = self._invoke_text(
            self.answer_prompt, {"question": question, "context": context}, temperature=0.2
        )
        return content or "信息不足"

    def chat_answer(self, question: str, context: str) -> str:
        content = self._invoke_text(
            self.chat_answer_prompt, {"question": question, "context": context}, temperature=0.2
        )
        return content or ""

    def answer_stream(self, question: str, context: str) -> Iterator[str]:
        yield from self._stream_text(
            self.answer_prompt, {"question": question, "context": context}, temperature=0.2
        )

    def chat_answer_stream(self, question: str, context: str) -> Iterator[str]:
        yield from self._stream_text(
            self.chat_answer_prompt, {"question": question, "context": context}, temperature=0.2
        )

    def classify_intent(self, question: str) -> str:
        result = self.classify_intent_with_meta(question)
        return result["intent"]

    def _rule_based_intent_vote(self, question: str) -> str:
        text = question.strip().lower()
        if not text:
            return "qa"
        chat_keywords = ("你好", "hi", "hello", "在吗", "聊聊", "随便聊", "晚安", "早上好")
        qa_keywords = ("什么是", "是什么", "如何", "为什么", "怎么", "多少", "哪些", "谁", "何时", "哪里")
        if any(k in text for k in chat_keywords):
            return "chat"
        if any(k in text for k in qa_keywords):
            return "qa"
        if re.search(r"[?？]$", question) or re.search(r"(吗|呢)$", question):
            return "qa"
        return "qa"

    def _is_greeting(self, question: str) -> bool:
        text = question.strip().lower()
        if not text:
            return False
        greetings = (
            "你好",
            "您好",
            "嗨",
            "hi",
            "hello",
            "早上好",
            "中午好",
            "下午好",
            "晚上好",
            "在吗",
        )
        if text in greetings:
            return True
        return any(text.startswith(g) and len(text) <= len(g) + 2 for g in greetings)

    def classify_intent_with_meta(self, question: str) -> dict:
        if self._is_greeting(question):
            return {
                "intent": "chat",
                "confidence": 1.0,
                "reason": "greeting_short_circuit",
                "raw_output": "",
                "fallback_used": False,
            }
        content = self._invoke_text(self.intent_prompt, {"question": question}, temperature=0)
        fallback_intent = self._rule_based_intent_vote(question)
        try:
            parsed = json.loads(content)
            raw_intent = str(parsed.get("intent", "")).strip().lower()
            intent = "chat" if raw_intent == "chat" else "qa"
            confidence = float(parsed.get("confidence", 0.5))
            confidence = max(0.0, min(1.0, confidence))
            reason = str(parsed.get("reason", ""))
            if confidence < self.settings.workflow_intent_low_confidence_threshold:
                return {
                    "intent": fallback_intent,
                    "confidence": confidence,
                    "reason": reason or "low_confidence_fallback",
                    "raw_output": content,
                    "fallback_used": True,
                }
            return {
                "intent": intent,
                "confidence": confidence,
                "reason": reason or "model_classification",
                "raw_output": content,
                "fallback_used": False,
            }
        except (json.JSONDecodeError, TypeError, ValueError):
            return {
                "intent": fallback_intent,
                "confidence": 0.0,
                "reason": "invalid_json_fallback",
                "raw_output": content,
                "fallback_used": True,
            }

    def detect_malicious_input(self, question: str) -> list[str]:
        try:
            content = self._invoke_text(self.security_prompt, {"question": question}, temperature=0)
            parsed = json.loads(content)
        except Exception:
            return []
        if bool(parsed.get("malicious", False)):
            reason = str(parsed.get("reason", "llm_detected_risk")).strip() or "llm_detected_risk"
            return [f"malicious_llm:{reason}"]
        return []

    def build_chat_context(self, question: str) -> str:
        content = self._invoke_text(self.chat_context_prompt, {"question": question}, temperature=0.1)
        return content or question

    def rewrite_qa_question(self, question: str) -> str:
        content = self._invoke_text(self.rewrite_prompt, {"question": question}, temperature=0.1)
        return content or question

    def compress_history(self, history_text: str) -> str:
        content = self._invoke_text(
            self.compress_prompt, {"history": history_text}, temperature=0.1
        )
        return content or history_text

    def evaluate_chat_answer(self, question: str, answer: str) -> dict:
        content = self._invoke_text(
            self.chat_eval_prompt, {"question": question, "answer": answer}, temperature=0
        )
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            parsed = {}
        score = int(parsed.get("score", 6))
        return {
            "score": max(0, min(10, score)),
            "threshold": int(parsed.get("threshold", 7)),
            "suggestion": str(parsed.get("suggestion", "请补充证据并提升表达清晰度。")),
        }

    def evaluate_qa_answer(self, question: str, context: str, answer: str) -> dict:
        content = self._invoke_text(
            self.qa_eval_prompt,
            {"question": question, "context": context, "answer": answer},
            temperature=0,
        )
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            parsed = {}
        return {
            "retrieval_ok": bool(parsed.get("retrieval_ok", True)),
            "answer_ok": bool(parsed.get("answer_ok", False)),
            "retrieval_score": int(parsed.get("retrieval_score", 6)),
            "answer_score": int(parsed.get("answer_score", 6)),
            "suggestion": str(parsed.get("suggestion", "请补充更相关证据，并使回答对齐提问。")),
        }
