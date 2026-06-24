"""RAG pipeline extension point.

本模組保留 Data ingestion -> Chunking -> Embedding -> Indexing -> Retrieval
的程式擴充位置。V1 只存 wiki_sources，不啟用 chunking/vector retrieval。
"""

from app.models.domain import KnowledgeChunk, RagSource, WikiSource
from app.crud.protocols import RepositoryProtocol


class RagPipelineService:
    """保留未來 RAG pipeline 的 service 介面。"""

    def __init__(self, repository: RepositoryProtocol) -> None:
        self.repository = repository

    def chunk_and_store(self, event_id: str, sources: list[WikiSource]) -> list[KnowledgeChunk]:
        """未來負責 chunking；目前固定回傳空陣列。"""
        return []

    def retrieve(self, event_id: str, user_message: str, limit: int = 3) -> list[RagSource]:
        """未來負責 retrieval；目前不注入任何 RAG source。"""
        return []
