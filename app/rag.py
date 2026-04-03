"""RAG knowledge setup backed by ChromaDB."""

import asyncio
import os

from agno.knowledge.knowledge import Knowledge
from agno.knowledge.embedder.google import GeminiEmbedder
from agno.vectordb.chroma import ChromaDb
from agno.vectordb.search import SearchType

from app.config import CHROMADB_PATH, GOOGLE_API_KEY

knowledge = Knowledge(
    name="HomeFirst Policy Knowledge Base",
    description="HomeFirst loan policies, documents, PMAY, tax, and FAQs.",
    vector_db=ChromaDb(
        collection="homefirst_docs",
        path=CHROMADB_PATH,
        persistent_client=True,
        embedder=GeminiEmbedder(api_key=GOOGLE_API_KEY),
        search_type=SearchType.hybrid,
    ),
)


def ingest_knowledge_base() -> None:
    """Ingest text docs from knowledge_base/docs."""
    docs_dir = os.path.join(os.path.dirname(__file__), "..", "knowledge_base", "docs")

    async def _ingest_all() -> None:
        for filename in sorted(os.listdir(docs_dir)):
            filepath = os.path.join(docs_dir, filename)
            if filename.endswith((".txt", ".md", ".markdown")):
                print(f"Ingesting: {filename}")
                await knowledge.ainsert(
                    path=filepath,
                    name=os.path.splitext(filename)[0],
                    skip_if_exists=True,
                )

    asyncio.run(_ingest_all())
    print("Knowledge base ingestion complete.")


if __name__ == "__main__":
    ingest_knowledge_base()
