import json
from collections.abc import Mapping
from typing import Any

from app.schemas.query import PromptBuildResult, QueryType


class PromptBuilder:
    """Build LLM prompts from a query type and Neo4j context."""

    _NO_CONTEXT_MESSAGE = (
        "No Neo4j knowledge-base context was found for this question. "
        "You MUST tell the user that this entity or topic is not present in "
        "the knowledge base. DO NOT answer from your own training data. "
        "DO NOT speculate or guess what the entity might be. "
        "Simply state that the knowledge base does not contain information "
        "about this topic and suggest the user rephrase or ask about a "
        "different AI/ML concept."
    )
    _COMMON_INSTRUCTIONS = (
        "You are a RAG assistant for a university knowledge base about AI, "
        "machine learning, and large language models. Use the Neo4j context "
        "as the primary source of truth. Do not invent relationships that are "
        "not present in the context."
    )
    _LANGUAGE_INSTRUCTIONS: dict[str, str] = {
        "ru": (
            "ВАЖНО: ты ОБЯЗАН отвечать ТОЛЬКО на русском языке. "
            "Даже если контекст и названия сущностей на английском — "
            "весь текст ответа должен быть на русском. "
            "Технические термины (BERT, GPT, Fine-tuning и т.д.) можно оставлять как есть."
        ),
        "en": (
            "IMPORTANT: you MUST respond in English only."
        ),
    }
    _TEMPLATES = {
        QueryType.DEFINITION: (
            "Task: define the requested entity. Explain what it is, mention "
            "its type (Model / Method / Concept / Task / Framework) when available, "
            "describe its purpose, and cite 2-3 most relevant neighboring concepts "
            "or relationships from the context. Give a paragraph-length answer."
        ),
        QueryType.COMPARISON: (
            "Task: compare the requested entities side by side. Use a structured "
            "format (e.g. bullet points per entity). Cover: tasks each is used for, "
            "methods each uses, frameworks, and any direct IS_A / RELATED_TO links. "
            "Conclude with a one-sentence summary of the key difference."
        ),
        QueryType.CAPABILITIES: (
            "Task: explain what the requested model or concept is used for. "
            "List each task from the USED_FOR relationships and write 1-2 sentences "
            "explaining what that task means in practice. "
            "Also mention the most important methods the entity uses if available."
        ),
        QueryType.METHODS: (
            "Task: list and explain the methods or techniques used by the requested "
            "entity. For each method from the USES relationships, write 1-2 sentences "
            "explaining what it is and why it matters for this entity."
        ),
        QueryType.RECOMMENDATION: (
            "Task: make a recommendation based only on the available context. "
            "State criteria, trade-offs, and explicitly note when the context "
            "is insufficient to give a confident answer."
        ),
        QueryType.UNKNOWN: (
            "Task: answer the question using the available context. "
            "Explain what type of entity was found, its relationships, "
            "and any relevant properties. Give a helpful paragraph-length answer."
        ),
    }

    def build(
        self,
        query_type: QueryType,
        user_question: str,
        context: Mapping[str, Any] | None,
        language: str = "ru",
    ) -> PromptBuildResult:
        """Build a prompt for the LLM.

        Args:
            query_type: Classified user query type.
            user_question: Original user question.
            context: Structured Neo4j context for the question.
            language: Response language code ("ru" or "en").

        Returns:
            Prompt text and a warning flag for empty context.
        """
        lang_instruction = self._LANGUAGE_INSTRUCTIONS.get(
            language, self._LANGUAGE_INSTRUCTIONS["en"]
        )
        if not context:
            return PromptBuildResult(
                prompt=self._build_fallback_prompt(
                    query_type, user_question, lang_instruction
                ),
                warning=True,
            )

        template = self._TEMPLATES.get(query_type, self._TEMPLATES[QueryType.UNKNOWN])
        context_json = self._serialize_context(context)
        prompt = "\n\n".join(
            [
                self._COMMON_INSTRUCTIONS,
                lang_instruction,
                template,
                f"Query type: {query_type.value}",
                f"User question: {user_question}",
                "Neo4j context:",
                context_json,
                "Final answer:",
            ]
        )
        return PromptBuildResult(prompt=prompt, warning=False)

    def _build_fallback_prompt(
        self,
        query_type: QueryType,
        user_question: str,
        lang_instruction: str,
    ) -> str:
        """Build a prompt used when no Neo4j context is available."""
        template = self._TEMPLATES.get(query_type, self._TEMPLATES[QueryType.UNKNOWN])
        return "\n\n".join(
            [
                self._COMMON_INSTRUCTIONS,
                lang_instruction,
                self._NO_CONTEXT_MESSAGE,
                template,
                f"Query type: {query_type.value}",
                f"User question: {user_question}",
                "Final answer:",
            ]
        )

    def _serialize_context(self, context: Mapping[str, Any]) -> str:
        """Serialize structured context in a stable JSON format."""
        return json.dumps(context, ensure_ascii=False, indent=2, sort_keys=True)


def build_prompt(
    query_type: QueryType,
    user_question: str,
    context: Mapping[str, Any] | None,
) -> PromptBuildResult:
    """Build a prompt with the default prompt builder.

    Args:
        query_type: Classified user query type.
        user_question: Original user question.
        context: Structured Neo4j context for the question.

    Returns:
        Prompt text and a warning flag for empty context.
    """
    return PromptBuilder().build(query_type, user_question, context)
