"""CRUD layer package.

匯出 RepositoryProtocol 作為資料存取層的唯一抽象介面。
所有 service 與 endpoint 皆透過此 Protocol 操作資料，
不直接依賴 Supabase 或 in-memory 實作。
"""

from .protocols import RepositoryProtocol

__all__ = ["RepositoryProtocol"]
