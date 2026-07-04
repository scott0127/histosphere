"""Database / repository implementations package.

匯出兩種 RepositoryProtocol 的具體實作:
    - ``InMemoryRepository``: 純 Python dict 存儲，供測試與開發使用。
    - ``SupabaseRepository``: 透過 PostgREST 連接 Supabase/PostgreSQL。
"""

from .in_memory import InMemoryRepository
from .supabase_repository import SupabaseRepository

__all__ = ["InMemoryRepository", "SupabaseRepository"]
