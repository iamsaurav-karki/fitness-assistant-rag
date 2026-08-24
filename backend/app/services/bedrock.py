import boto3
from botocore.config import Config

from app.config import settings


class BedrockRuntimeClient:
    def __init__(self) -> None:
        self.client = boto3.client(
            "bedrock-runtime", region_name=settings.aws_region,
            config=Config(connect_timeout=5, read_timeout=90, retries={"max_attempts": 2, "mode": "standard"}),
        )

    def answer(self, question: str, context: str, system_prompt: str) -> str:
        if not settings.model_id:
            raise RuntimeError("BEDROCK_MODEL_ID is not configured")

        response = self.client.converse(
            modelId=settings.model_id,
            system=[{"text": system_prompt}],
            messages=[{"role": "user", "content": [{"text": f"Context:\n{context}\n\nQuestion: {question}"}]}],
            inferenceConfig={"maxTokens": 700, "temperature": 0.2},
        )
        return response["output"]["message"]["content"][0]["text"]