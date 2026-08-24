import argparse
import json

from app.config import settings
from app.services.knowledge_base import KnowledgeBaseClient


def main() -> None:
    parser = argparse.ArgumentParser(description="Test Bedrock Knowledge Bases retrieval")
    parser.add_argument("question")
    question = parser.parse_args().question
    results = KnowledgeBaseClient().retrieve(question)

    print(f"Question:\n{question}\n\nRetrieved documents:")
    for index, result in enumerate(results, start=1):
        print(f"\n{index}. score: {result.get('score')}")
        print(f"text: {result.get('content', {}).get('text', '')}")
        print(f"metadata: {json.dumps(result.get('location', {}), default=str)}")


if __name__ == "__main__":
    main()