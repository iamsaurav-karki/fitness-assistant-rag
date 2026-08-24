from typing import Any
from urllib.parse import urlparse

import boto3
from botocore.config import Config

from app.config import settings


class KnowledgeBaseClient:
    def __init__(self) -> None:
        self.client = boto3.client(
            "bedrock-agent-runtime", region_name=settings.aws_region,
            config=Config(connect_timeout=5, read_timeout=45, retries={"max_attempts": 2, "mode": "standard"}),
        )

    def retrieve(self, question: str) -> list[dict[str, Any]]:
        if not settings.knowledge_base_id:
            raise RuntimeError("BEDROCK_KNOWLEDGE_BASE_ID is not configured")

        response = self.client.retrieve(
            knowledgeBaseId=settings.knowledge_base_id,
            retrievalQuery={"text": question},
            retrievalConfiguration={
                "managedSearchConfiguration": {"numberOfResults": settings.retrieval_results}
            },
        )
        return response.get("retrievalResults", [])

    def retrieve_managed(self, question: str, number_of_results: int | None = None) -> list[dict[str, Any]]:
        """Retrieve semantic candidates for exploratory questions."""
        if not settings.knowledge_base_id:
            raise RuntimeError("BEDROCK_KNOWLEDGE_BASE_ID is not configured")
        response = self.client.retrieve(
            knowledgeBaseId=settings.knowledge_base_id,
            retrievalQuery={"text": question},
            retrievalConfiguration={"managedSearchConfiguration": {
                "numberOfResults": number_of_results or settings.retrieval_results,
            }},
        )
        return response.get("retrievalResults", [])


def source_from_result(result: dict[str, Any]) -> dict[str, Any]:
    location = result.get("location") or {}
    s3_location = location.get("s3Location") or {}
    uri = s3_location.get("uri")
    document = urlparse(uri).path.rsplit("/", 1)[-1] if uri else "Knowledge base document"
    return {"document": document or "Knowledge base document", "uri": uri}