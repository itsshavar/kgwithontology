import json
import os
import re
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

import httpx

ENTITY_PATTERN = r"[A-Z][A-Za-z0-9&._-]*(?:\s+[A-Z][A-Za-z0-9&._-]*){0,3}"
COMMON_ENTITY_STOPWORDS = {
    "A",
    "An",
    "And",
    "As",
    "At",
    "By",
    "For",
    "From",
    "He",
    "Her",
    "His",
    "I",
    "If",
    "In",
    "It",
    "Its",
    "On",
    "Or",
    "Our",
    "She",
    "That",
    "The",
    "Their",
    "There",
    "They",
    "This",
    "These",
    "Those",
    "We",
    "With",
    "You",
}
OBJECT_RELATION_PHRASES = [
    "works for",
    "belongs to",
    "part of",
    "located in",
    "lives in",
    "member of",
    "reports to",
    "collaborates with",
    "related to",
    "uses",
    "owns",
    "causes",
    "treats",
    "manages",
    "supports",
]
CLASS_PATTERNS = [
    re.compile(rf"\b(?P<subject>{ENTITY_PATTERN})\b\s+is\s+an?\s+(?P<class>[A-Za-z][A-Za-z0-9_-]+)\b", re.IGNORECASE),
    re.compile(rf"\b(?P<subject>{ENTITY_PATTERN})\b\s+works\s+as\s+an?\s+(?P<class>[A-Za-z][A-Za-z0-9_-]+)\b", re.IGNORECASE),
]
DATA_PATTERNS = [
    re.compile(
        rf"\b(?P<subject>{ENTITY_PATTERN})\b\s+(?:has|had)\s+(?:an?\s+)?(?P<attribute>[a-z][a-zA-Z0-9_\- ]{{1,30}}?)\s+(?:of\s+)?(?P<value>[^.;,]{{1,80}})",
        re.IGNORECASE,
    ),
    re.compile(
        rf"\b(?P<subject>{ENTITY_PATTERN})\b'?s\s+(?P<attribute>[a-z][a-zA-Z0-9_\- ]{{1,30}}?)\s+is\s+(?P<value>[^.;,]{{1,80}})",
        re.IGNORECASE,
    ),
]


@dataclass
class EntityMention:
    text: str
    sentence: str
    label: str | None = None
    source: str = "regex"


@dataclass
class TypedEntityCandidate:
    subject: str
    class_name: str
    sentence: str
    source: str = "pattern"


@dataclass
class ObjectRelationCandidate:
    subject: str
    predicate: str
    object_name: str
    sentence: str
    source: str = "pattern"


@dataclass
class DataRelationCandidate:
    subject: str
    attribute: str
    value: str
    sentence: str
    source: str = "pattern"


@dataclass
class ExtractionAnalysis:
    sentences: list[str] = field(default_factory=list)
    entity_mentions: list[EntityMention] = field(default_factory=list)
    typed_entities: list[TypedEntityCandidate] = field(default_factory=list)
    object_relations: list[ObjectRelationCandidate] = field(default_factory=list)
    data_relations: list[DataRelationCandidate] = field(default_factory=list)


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip())


def _clean_entity_name(value: str) -> str:
    return _normalize_text(value.strip(" \t\n\r.,;:!?()[]{}\"'"))


def _regex_sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", text or "") if part and part.strip()]


class OptionalLLMCanonicalizer:
    def __init__(self) -> None:
        self.api_url = os.getenv("LLM_API_URL")
        self.api_key = os.getenv("LLM_API_KEY")
        self.model = os.getenv("LLM_MODEL")
        self.enabled = bool(self.api_url and self.api_key and self.model)

    def canonicalize_relation(self, phrase: str, known_properties: list[str]) -> str:
        if not self.enabled or not known_properties:
            return phrase

        prompt = (
            "You map a relation phrase to one ontology property name. "
            "Return JSON only with key canonical_name. "
            f"Phrase: {phrase}\n"
            f"Known properties: {known_properties[:50]}"
        )
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a strict ontology relation canonicalizer."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0,
        }
        try:
            with httpx.Client(timeout=15.0) as client:
                response = client.post(self.api_url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                parsed = json.loads(content)
                canonical = parsed.get("canonical_name")
                if isinstance(canonical, str) and canonical.strip():
                    return canonical.strip()
        except Exception:
            return phrase
        return phrase


class HybridExtractionPipeline:
    def __init__(self) -> None:
        self.spacy_nlp = None
        self.transformer_ner = None
        self.transformer_enabled = os.getenv("ENABLE_TRANSFORMERS", "false").lower() in {"1", "true", "yes"}
        self.transformer_model = os.getenv("TRANSFORMER_NER_MODEL")
        self.spacy_model = os.getenv("SPACY_MODEL", "en_core_web_sm")
        self.llm = OptionalLLMCanonicalizer()
        self._init_spacy()
        self._init_transformers()

    def _init_spacy(self) -> None:
        try:
            import spacy

            try:
                self.spacy_nlp = spacy.load(self.spacy_model)
            except Exception:
                nlp = spacy.blank("en")
                if "sentencizer" not in nlp.pipe_names:
                    nlp.add_pipe("sentencizer")
                self.spacy_nlp = nlp
        except Exception:
            self.spacy_nlp = None

    def _init_transformers(self) -> None:
        if not self.transformer_enabled or not self.transformer_model:
            return
        try:
            from transformers import pipeline

            self.transformer_ner = pipeline(
                "token-classification",
                model=self.transformer_model,
                aggregation_strategy="simple",
            )
        except Exception:
            self.transformer_ner = None

    def _spacy_sentences(self, text: str) -> list[str]:
        if not self.spacy_nlp:
            return _regex_sentences(text)

        doc = self.spacy_nlp(text)
        sentences = [sent.text.strip() for sent in getattr(doc, "sents", []) if sent.text and sent.text.strip()]
        return sentences or _regex_sentences(text)

    def _spacy_entities(self, text: str) -> list[EntityMention]:
        if not self.spacy_nlp:
            return []
        try:
            doc = self.spacy_nlp(text)
        except Exception:
            return []

        entities: list[EntityMention] = []
        for ent in getattr(doc, "ents", []):
            cleaned = _clean_entity_name(ent.text)
            if not cleaned or cleaned in COMMON_ENTITY_STOPWORDS:
                continue
            if getattr(ent, "label_", "") in {"CARDINAL", "DATE", "TIME", "ORDINAL", "MONEY", "PERCENT", "QUANTITY"}:
                continue
            sentence = ent.sent.text.strip() if getattr(ent, "sent", None) else text[:200]
            entities.append(
                EntityMention(
                    text=cleaned,
                    sentence=sentence,
                    label=getattr(ent, "label_", None),
                    source="spacy",
                )
            )
        return entities

    def _regex_entity_mentions(self, sentence: str) -> list[EntityMention]:
        mentions: list[EntityMention] = []
        for raw in re.findall(rf"\b({ENTITY_PATTERN})\b", sentence):
            cleaned = _clean_entity_name(raw)
            if not cleaned or cleaned in COMMON_ENTITY_STOPWORDS or len(cleaned) == 1:
                continue
            mentions.append(EntityMention(text=cleaned, sentence=sentence, source="regex"))
        return mentions

    def _transformer_entities(self, sentences: list[str]) -> list[EntityMention]:
        if not self.transformer_ner:
            return []
        entities: list[EntityMention] = []
        for sentence in sentences[:100]:
            try:
                results = self.transformer_ner(sentence)
            except Exception:
                continue
            for item in results:
                entity_group = item.get("entity_group") or item.get("entity")
                if entity_group in {"CARDINAL", "DATE", "TIME", "MONEY", "PERCENT", "ORDINAL"}:
                    continue
                word = item.get("word") or item.get("text")
                cleaned = _clean_entity_name(word or "")
                if not cleaned or cleaned in COMMON_ENTITY_STOPWORDS:
                    continue
                entities.append(EntityMention(text=cleaned, sentence=sentence, label=entity_group, source="transformer"))
        return entities

    def _pattern_relations(
        self,
        sentences: list[str],
        known_properties: list[str],
    ) -> tuple[list[TypedEntityCandidate], list[ObjectRelationCandidate], list[DataRelationCandidate]]:
        typed_entities: list[TypedEntityCandidate] = []
        object_relations: list[ObjectRelationCandidate] = []
        data_relations: list[DataRelationCandidate] = []

        for sentence in sentences:
            for pattern in CLASS_PATTERNS:
                for match in pattern.finditer(sentence):
                    typed_entities.append(
                        TypedEntityCandidate(
                            subject=_clean_entity_name(match.group("subject")),
                            class_name=_normalize_text(match.group("class")),
                            sentence=sentence,
                            source="pattern",
                        )
                    )

            for phrase in OBJECT_RELATION_PHRASES:
                relation_pattern = re.compile(
                    rf"\b(?P<subject>{ENTITY_PATTERN})\b\s+{re.escape(phrase)}\s+\b(?P<object>{ENTITY_PATTERN})\b",
                    re.IGNORECASE,
                )
                for match in relation_pattern.finditer(sentence):
                    canonical_phrase = self.llm.canonicalize_relation(phrase, known_properties)
                    object_relations.append(
                        ObjectRelationCandidate(
                            subject=_clean_entity_name(match.group("subject")),
                            predicate=_normalize_text(canonical_phrase),
                            object_name=_clean_entity_name(match.group("object")),
                            sentence=sentence,
                            source="pattern",
                        )
                    )

            for pattern in DATA_PATTERNS:
                for match in pattern.finditer(sentence):
                    attribute_name = match.group("attribute").strip()
                    attribute_name = re.sub(r"^(?:the|a|an)\s+", "", attribute_name, flags=re.IGNORECASE)
                    attribute_name = self.llm.canonicalize_relation(attribute_name, known_properties)
                    data_relations.append(
                        DataRelationCandidate(
                            subject=_clean_entity_name(match.group("subject")),
                            attribute=_normalize_text(attribute_name),
                            value=match.group("value").strip().strip("\"'"),
                            sentence=sentence,
                            source="pattern",
                        )
                    )
        return typed_entities, object_relations, data_relations

    def analyze_document(self, text: str, known_properties: list[str] | None = None) -> ExtractionAnalysis:
        known_properties = known_properties or []
        sentences = self._spacy_sentences(text)
        analysis = ExtractionAnalysis(sentences=sentences)

        seen_entities: set[tuple[str, str]] = set()

        def add_entity_mentions(items: list[EntityMention]) -> None:
            for item in items:
                key = (_normalize_text(item.text).lower(), _normalize_text(item.sentence).lower())
                if key in seen_entities:
                    continue
                seen_entities.add(key)
                analysis.entity_mentions.append(item)

        add_entity_mentions(self._spacy_entities(text))
        add_entity_mentions(self._transformer_entities(sentences))
        for sentence in sentences:
            add_entity_mentions(self._regex_entity_mentions(sentence))

        typed_entities, object_relations, data_relations = self._pattern_relations(sentences, known_properties)
        analysis.typed_entities.extend(typed_entities)
        analysis.object_relations.extend(object_relations)
        analysis.data_relations.extend(data_relations)
        return analysis


@lru_cache(maxsize=1)
def get_hybrid_extraction_pipeline() -> HybridExtractionPipeline:
    return HybridExtractionPipeline()
