import json
import re
from typing import Protocol

from app.core.config import settings
from app.schemas.llm import LLMGenerationResult
from app.schemas.query import ClassificationResult, QueryType

_U = re.UNICODE


class ClassifierLLMProtocol(Protocol):
    """Protocol for an LLM client used by the classifier."""

    async def generate(self, prompt: str) -> LLMGenerationResult:
        """Generate text from a prepared prompt."""


def _compile(*patterns: str) -> tuple[re.Pattern[str], ...]:
    return tuple(re.compile(p, _U) for p in patterns)


class QueryClassifier:
    """Hybrid classifier for user questions.

    Main mode:
    - LLM-based classification.

    Fallback mode:
    - deterministic rule-based classification.

    Entity extraction remains rule-based and deterministic.
    """

    _COMPARISON_PATTERNS = _compile(
        r"\bvs\.?\b",
        r"\bversus\b",
        r"\bcompare\b",
        r"\bdifference\b",
        r"\bdiffers?\b",
        r"(?<!\w)отлича\w+",
        r"(?<!\w)сравн\w+",
        r"(?<!\w)разниц\w+",
        r"(?<!\w)чем(?!\w).+?(?<!\w)от(?!\w)",
    )

    _METHODS_PATTERNS = _compile(
        r"\bmethod\w*\b",
        r"\btechnique\w*\b",
        r"\bapproach\w*\b",
        r"(?<!\w)метод\w*",
        r"(?<!\w)подход\w*",
        r"(?<!\w)техник\w*",
        r"(?<!\w)алгоритм\w*",
    )

    _CAPABILITIES_PATTERNS = _compile(
        r"\bused\s+for\b",
        r"\bcapabilit\w*\b",
        r"\bapplication\w*\b",
        r"\buse\s+case\w*\b",
        r"(?<!\w)использу\w+",
        r"(?<!\w)примен\w+",
        r"для\s+чего",
        r"(?<!\w)зачем(?!\w)",
        r"(?<!\w)назначени\w+",
    )

    _RECOMMENDATION_PATTERNS = _compile(
        r"\brecommend\w*\b",
        r"\bchoose\b",
        r"\bselect\b",
        r"\bbest\b",
        r"\bwhich\b.+\bfor\b",
        r"какой.+выбрать",
        r"что.+выбрать",
        r"(?<!\w)посовет\w+",
        r"(?<!\w)лучш\w+",
    )

    _DEFINITION_PATTERNS = _compile(
        r"\bwhat\s+is\b",
        r"\bdefine\b",
        r"\bdefinition\b",
        r"\bmeaning\b",
        r"что\s+такое",
        r"дай\s+определение",
        r"(?<!\w)определение(?!\w)",
        r"(?<!\w)объясни(?!\w)",
    )

    _QUOTED_ENTITY_PATTERN = re.compile(r"[\"'«“](.+?)[\"'»”]")
    _TOKEN_PATTERN = re.compile(r"[A-Za-zА-Яа-яЁё0-9.+-]+")

    _STOP_ENTITIES = {
        "Hello",
        "Hi",
        "What",
        "Which",
        "Compare",
        "Definition",
        "Что",
        "Чем",
        "Какие",
        "Какой",
        "Для",
    }

    _CLASSIFIER_PROMPT_TEMPLATE = """
You are a query classifier for a reference RAG system about artificial intelligence technologies.

Classify the user question into exactly one query type.

Allowed query types:
- definition: the user asks what a term, method, model, architecture or tool means;
- comparison: the user asks to compare two or more technologies, models, methods or tools;
- capabilities: the user asks what something is used for or what tasks it can solve;
- methods: the user asks what methods, approaches, techniques or algorithms something uses;
- recommendation: the user asks to choose, recommend or select a tool, model, method or approach;
- unknown: the type cannot be determined.

Return only one JSON object without markdown and without explanations.

Strict format:
{{"query_type": "definition"}}

User question:
{text}
"""

    def classify(self, text: str) -> ClassificationResult:
        """Classify raw user text using deterministic rules."""
        normalized_text = self._normalize_text(text)
        query_type = self._detect_query_type(normalized_text)
        entities = self._extract_entities(text)

        return ClassificationResult(
            query_type=query_type,
            entities=entities,
            classification_source="rules",
        )

    async def classify_with_llm_fallback(
        self,
        text: str,
        llm_client: ClassifierLLMProtocol,
    ) -> ClassificationResult:
        """Classify query through LLM first, then fallback to rules."""
        rules_result = self.classify(text)

        if not settings.query_classifier_use_llm:
            return rules_result

        try:
            llm_query_type = await self._classify_query_type_with_llm(
                text=text,
                llm_client=llm_client,
            )

            if llm_query_type == QueryType.UNKNOWN and rules_result.query_type != QueryType.UNKNOWN:
                return rules_result

            return ClassificationResult(
                query_type=llm_query_type,
                entities=rules_result.entities,
                classification_source="llm",
            )

        except Exception:
            return rules_result

    async def _classify_query_type_with_llm(
        self,
        text: str,
        llm_client: ClassifierLLMProtocol,
    ) -> QueryType:
        prompt = self._CLASSIFIER_PROMPT_TEMPLATE.format(text=text)
        result = await llm_client.generate(prompt)

        return self._parse_llm_query_type(result.text)

    def _parse_llm_query_type(self, content: str) -> QueryType:
        cleaned = content.strip()
        cleaned = cleaned.replace("```json", "").replace("```", "").strip()

        try:
            data = json.loads(cleaned)
            value = data.get("query_type") or data.get("type")

            return self._to_query_type(value)

        except Exception:
            pass

        match = re.search(
            r'"(?:query_type|type)"\s*:\s*"(definition|comparison|capabilities|methods|recommendation|unknown)"',
            cleaned,
            re.IGNORECASE,
        )

        if match:
            return self._to_query_type(match.group(1))

        match = re.search(
            r"\b(definition|comparison|capabilities|methods|recommendation|unknown)\b",
            cleaned,
            re.IGNORECASE,
        )

        if match:
            return self._to_query_type(match.group(1))

        raise ValueError(f"Cannot parse query type from LLM response: {content}")

    def _to_query_type(self, value: str | None) -> QueryType:
        if value is None:
            raise ValueError("LLM response does not contain query type.")

        normalized = value.strip().lower()

        for query_type in QueryType:
            if query_type.value == normalized:
                return query_type

        raise ValueError(f"Unsupported query type from LLM: {value}")

    def _detect_query_type(self, normalized_text: str) -> QueryType:
        """Return the first matching query type by priority."""
        pattern_groups = (
            (QueryType.COMPARISON, self._COMPARISON_PATTERNS),
            (QueryType.RECOMMENDATION, self._RECOMMENDATION_PATTERNS),
            (QueryType.METHODS, self._METHODS_PATTERNS),
            (QueryType.CAPABILITIES, self._CAPABILITIES_PATTERNS),
            (QueryType.DEFINITION, self._DEFINITION_PATTERNS),
        )

        for query_type, patterns in pattern_groups:
            if any(p.search(normalized_text) for p in patterns):
                return query_type

        return QueryType.UNKNOWN

    def _extract_entities(self, text: str) -> list[str]:
        """Extract likely entity names from raw user text."""
        candidates = [
            match.group(1).strip()
            for match in self._QUOTED_ENTITY_PATTERN.finditer(text)
        ]

        candidates.extend(self._extract_token_entities(text))

        return self._dedupe_entities(candidates)

    def _extract_token_entities(self, text: str) -> list[str]:
        """Extract entity candidates from capitalized/acronym token runs."""
        entities: list[str] = []
        current_tokens: list[str] = []

        for match in self._TOKEN_PATTERN.finditer(text):
            token = match.group(0)

            if self._is_entity_token(token):
                current_tokens.append(token)
                continue

            if current_tokens:
                entities.append(" ".join(current_tokens))
                current_tokens = []

        if current_tokens:
            entities.append(" ".join(current_tokens))

        return entities

    def _dedupe_entities(self, candidates: list[str]) -> list[str]:
        """Remove duplicates and obvious question words while preserving order."""
        entities: list[str] = []
        seen: set[str] = set()

        for candidate in candidates:
            entity = candidate.strip(" .,?!:;()[]{}")

            if not entity or entity in self._STOP_ENTITIES:
                continue

            key = entity.casefold()

            if key not in seen:
                seen.add(key)
                entities.append(entity)

        return entities

    def _is_entity_token(self, token: str) -> bool:
        """Return whether a token looks like an entity name part."""
        if token in self._STOP_ENTITIES:
            return False

        if len(token) < 2:
            return False

        if token.isupper():
            return True

        if token[0].isupper():
            return True

        return any(char.isupper() for char in token[1:])

    def _normalize_text(self, text: str) -> str:
        """Normalize text for pattern matching."""
        return re.sub(r"\s+", " ", text.casefold()).strip()


def classify_query(text: str) -> ClassificationResult:
    """Classify raw user text with the default rule-based classifier."""
    return QueryClassifier().classify(text)