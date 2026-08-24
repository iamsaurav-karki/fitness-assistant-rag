import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parents[1] / ".env")


@dataclass(frozen=True)
class Settings:
    aws_region: str = os.getenv("AWS_REGION", "us-east-1")
    knowledge_base_id: str = os.getenv("BEDROCK_KNOWLEDGE_BASE_ID", "")
    model_id: str = os.getenv("BEDROCK_MODEL_ID", "")
    retrieval_results: int = int(os.getenv("BEDROCK_RETRIEVAL_RESULTS", "15"))
    source_bucket: str = os.getenv("RAG_SOURCE_BUCKET", "fitness-assistant-test-saurav")
    source_key: str = os.getenv("RAG_SOURCE_KEY", "data.csv")
    cors_origins: tuple[str, ...] = tuple(
        origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if origin.strip()
    )


settings = Settings()