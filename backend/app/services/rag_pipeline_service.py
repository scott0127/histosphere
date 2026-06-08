from app.models.domain import KnowledgeChunk, RagSource, WikiSource
from app.crud.protocols import RepositoryProtocol


class RagPipelineService:
    """V1 extension point for future RAG.

    Data ingestion is already represented by wiki_sources. Chunking, embedding,
    indexing, and retrieval are intentionally postponed until the research design
    decides how source comparison and cross-lingual retrieval should work.
    """

    def __init__(self, repository: RepositoryProtocol) -> None:
        self.repository = repository

    def chunk_and_store(self, event_id: str, sources: list[WikiSource]) -> list[KnowledgeChunk]:
        return []

    def retrieve(self, event_id: str, user_message: str, limit: int = 3) -> list[RagSource]:
        return []
