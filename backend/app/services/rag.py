from pathlib import Path
import csv
import logging
import time
from io import StringIO

import boto3

from app.config import settings
from app.services.bedrock import BedrockRuntimeClient
from app.services.knowledge_base import KnowledgeBaseClient, source_from_result


PROMPT_PATH = Path(__file__).parents[1] / "prompts" / "fitness_assistant.txt"
logger = logging.getLogger(__name__)
FITNESS_TERMS = {
    "exercise", "exercises", "workout", "workouts", "training", "fitness", "muscle",
    "chest", "back", "legs", "arms", "shoulder", "biceps", "triceps", "pectoral",
    "dumbbell", "barbell", "kettlebell", "cardio", "strength", "hypertrophy", "mobility",
    "stretch", "flexibility", "nutrition", "protein", "diet", "recovery", "beginner",
    "squat", "bench", "press", "deadlift", "gym", "weight", "weights",
}
STRUCTURED_SIGNALS = ("what exercises", "which exercises", "list exercises", "exercises for", "exercises that", "workouts for")
FILTERS = {
    "chest": ("muscle_groups_activated", ("pectoral",)),
    "pectoral": ("muscle_groups_activated", ("pectoral",)),
    "arms": ("muscle_groups_activated", ("biceps", "triceps", "forearm")),
    "legs": ("muscle_groups_activated", ("quadriceps", "hamstrings", "glutes", "calves")),
    "core": ("body_part", ("core",)),
    "back": ("body_part", ("back",)),
    "shoulders": ("muscle_groups_activated", ("deltoid",)),
    "biceps": ("muscle_groups_activated", ("biceps",)),
    "triceps": ("muscle_groups_activated", ("triceps",)),
    "dumbbell": ("type_of_equipment", ("dumbbell",)),
    "barbell": ("type_of_equipment", ("barbell",)),
    "bodyweight": ("type_of_equipment", ("bodyweight",)),
}


class RagService:
    def __init__(self) -> None:
        self.knowledge_base = KnowledgeBaseClient()
        self.runtime = BedrockRuntimeClient()
        self.system_prompt = PROMPT_PATH.read_text(encoding="utf-8")
        self.s3 = boto3.client("s3", region_name=settings.aws_region)
        self._rows: list[dict[str, str]] | None = None

    def _dataset_rows(self) -> list[dict[str, str]]:
        if self._rows is None:
            response = self.s3.get_object(Bucket=settings.source_bucket, Key=settings.source_key)
            text = response["Body"].read().decode("utf-8-sig")
            self._rows = list(csv.DictReader(StringIO(text)))
        return self._rows

    def _structured_matches(self, question: str) -> list[dict[str, str]] | None:
        lowered = question.lower()
        has_filter_term = any(term in lowered for term in FILTERS)
        if not any(signal in lowered for signal in STRUCTURED_SIGNALS) and not ("exercise" in lowered and has_filter_term):
            return None
        for term, (column, values) in FILTERS.items():
            if term in lowered:
                return [row for row in self._dataset_rows() if any(value in row.get(column, "").lower() for value in values)]
        return None

    @staticmethod
    def _row_context(rows: list[dict[str, str]]) -> str:
        fields = ("exercise_name", "type_of_activity", "type_of_equipment", "body_part", "type", "muscle_groups_activated", "instructions")
        return "\n\n---\n\n".join("\n".join(f"{field}: {row.get(field, '')}" for field in fields) for row in rows)

    def answer(self, question: str) -> tuple[str, list[dict]]:
        question_terms = set(question.lower().replace("?", "").split())
        if not question_terms.intersection(FITNESS_TERMS):
            return "I specialize in fitness questions, and I could not find this information in the fitness knowledge base.", []

        started = time.perf_counter()
        structured_rows = self._structured_matches(question)
        if structured_rows is not None:
            context = "EXHAUSTIVE STRUCTURED MATCHES. Every row below matches the requested filter.\n\n" + self._row_context(structured_rows)
            logger.info("rag_route=structured matches=%d row_ids=%s", len(structured_rows), [row.get("id") for row in structured_rows])
            source_rows = structured_rows
            results = []
            unique_text = [context]
        else:
            results = self.knowledge_base.retrieve_managed(question)
            source_rows = []
            unique_text = []
            seen_text = set()
            for result in results:
                text = (result.get("content", {}).get("text") or "").strip()
                if text and text not in seen_text:
                    seen_text.add(text)
                    unique_text.append(text)
            context = "\n\n---\n\n".join(unique_text)
        if not context:
            logger.info("rag_retrieval results=%d unique_chunks=0 total_ms=%.1f", len(results), (time.perf_counter() - started) * 1000)
            return "I could not find supporting information in the fitness knowledge base.", []

        retrieval_ms = (time.perf_counter() - started) * 1000
        generation_started = time.perf_counter()
        answer = self.runtime.answer(question, context, self.system_prompt)
        logger.info(
            "rag_request results=%d unique_chunks=%d retrieval_ms=%.1f generation_ms=%.1f total_ms=%.1f",
            len(results), len(unique_text), retrieval_ms,
            (time.perf_counter() - generation_started) * 1000,
            (time.perf_counter() - started) * 1000,
        )
        sources = []
        if source_rows:
            sources = [{"document": settings.source_key, "uri": f"s3://{settings.source_bucket}/{settings.source_key}"}]
            return answer.strip(), sources
        seen_sources = set()
        for result in results:
            source = source_from_result(result)
            if source["document"] not in seen_sources:
                seen_sources.add(source["document"])
                sources.append(source)
        return answer.strip(), sources