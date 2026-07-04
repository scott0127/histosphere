"""API schemas package.

匯出所有 API 請求與回應的 Pydantic schema。
Request schemas 定義前端送入的資料結構與驗證規則，
Response schemas 定義後端回傳的資料結構。
"""

from .requests import (
    ChatRequest,
    ConversationCreateRequest,
    EventCheckRequest,
    EventInitializeRequest,
    PersonaCreateRequest,
    PersonaUpdateRequest,
)
from .responses import (
    ChatResponse,
    ConversationCreateResponse,
    ConversationLoadResponse,
    EventInitializeResponse,
    EventListItem,
)

__all__ = [
    "ChatRequest",
    "ChatResponse",
    "ConversationCreateRequest",
    "ConversationCreateResponse",
    "ConversationLoadResponse",
    "EventCheckRequest",
    "EventInitializeRequest",
    "EventInitializeResponse",
    "EventListItem",
    "PersonaCreateRequest",
    "PersonaUpdateRequest",
]
