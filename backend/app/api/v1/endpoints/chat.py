"""Chat API endpoint.

本模組負責接收前端送出的 learner 訊息，並交給 ChatService 根據
2x2 實驗條件產生 generic chatbot 或 historical persona 回覆。

Routes:
    POST /api/chat: 處理單次 learner 對話訊息，回傳 AI 回覆與附加標注。
"""

import asyncio
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.api.deps import get_chat_service, require_active_participant_actor, require_session_actor
from app.core.auth import AuthenticatedActor
from app.core.learner_task_view import learner_view
from app.models.domain import ChatMessage
from app.schemas.requests import ChatRequest
from app.schemas.responses import ChatOperationStatusResponse, ChatResponse
from app.services import ChatService

router = APIRouter(prefix="/api", tags=["chat"])


def _require_conversation_access(
    request: ChatRequest,
    actor: AuthenticatedActor,
    service: ChatService,
) -> None:
    """確認 conversation 屬於目前 Auth user；admin mode 保留既有覆寫權限。"""
    _require_conversation_id_access(request.conversation_id, actor, service)


def _require_conversation_id_access(
    conversation_id: str,
    actor: AuthenticatedActor,
    service: ChatService,
) -> None:
    """以 conversation ID 驗證讀寫權，供送出與狀態查詢共用。"""
    conversation = service.repository.get_conversation(conversation_id)
    if not conversation:
        return
    owner_user_id = conversation.user_id
    session = None
    if not owner_user_id and conversation.session_id:
        session = service.repository.get_session(conversation.session_id)
        owner_user_id = session.user_id if session else None
    actor.require_owner(owner_user_id)
    if conversation.session_id and session is None:
        session = service.repository.get_session(conversation.session_id)
    require_session_actor(actor, service.repository, session)


def _sse_event(payload: dict) -> str:
    """將單一事件編碼成 SSE frame。"""
    event_type = str(payload.get("type", "message"))
    serialized = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return f"event: {event_type}\ndata: {serialized}\n\n"


def _response_chunks(content: str, size: int = 16) -> list[str]:
    """模型回覆通過完整審查後，再切成小段傳給前端。"""
    return [content[index:index + size] for index in range(0, len(content), size)]


def _consume_task_result(task: asyncio.Task) -> None:
    """讀取消失連線後的背景結果，避免未處理例外警告。"""
    try:
        task.result()
    except (asyncio.CancelledError, Exception):
        pass


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    actor: AuthenticatedActor = Depends(require_active_participant_actor),
    service: ChatService = Depends(get_chat_service),
) -> ChatResponse:
    """處理單次對話訊息，實際政策判斷與訊息儲存由 ChatService 負責。

    根據 conversation 關聯的 2x2 實驗條件，決定使用 generic chatbot 模式
    或 historical persona role-play 模式回覆。ChatService 內部會完成
    prompt 組裝、LLM 呼叫、annotation 擷取與訊息持久化。

    Args:
        request: 聊天請求，包含 conversation_id、user_message、
            可選的 history；target_persona_id 僅保留舊版相容且傳入會被拒絕。
        service: 由 Dependency Injection 注入的 ChatService 實例。

    Returns:
        ChatResponse: 包含 AI 回覆文字、選用的 persona、assistant 名稱、
            ChatMessage 紀錄、annotations、related_events、
            dynamic_context 以及 rag_sources。
    """
    _require_conversation_access(request, actor, service)
    return learner_view(await service.chat(request))


@router.get(
    "/chat/operations/{client_request_id}",
    response_model=ChatOperationStatusResponse,
)
async def chat_operation_status(
    client_request_id: str,
    conversation_id: str,
    actor: AuthenticatedActor = Depends(require_active_participant_actor),
    service: ChatService = Depends(get_chat_service),
) -> ChatOperationStatusResponse:
    """斷線或重整後查詢同一聊天回合，不會再次呼叫模型。"""
    _require_conversation_id_access(conversation_id, actor, service)
    return learner_view(service.get_operation_status(conversation_id, client_request_id))


@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    actor: AuthenticatedActor = Depends(require_active_participant_actor),
    service: ChatService = Depends(get_chat_service),
) -> StreamingResponse:
    """用 SSE 回傳保存狀態、等待狀態、已驗證文字片段與最終訊息。"""
    _require_conversation_access(request, actor, service)

    async def events() -> AsyncIterator[str]:
        persisted_message_future: asyncio.Future[ChatMessage] = (
            asyncio.get_running_loop().create_future()
        )
        message_was_persisted = False

        async def on_user_persisted(message: ChatMessage) -> None:
            if not persisted_message_future.done():
                persisted_message_future.set_result(message)

        chat_task = asyncio.create_task(
            service.chat(request, on_user_persisted=on_user_persisted)
        )

        try:
            done, _ = await asyncio.wait(
                {chat_task, persisted_message_future},
                return_when=asyncio.FIRST_COMPLETED,
            )
            if chat_task in done and not persisted_message_future.done():
                # 代表請求在保存 learner 訊息前就被 session/condition 驗證拒絕。
                await chat_task

            persisted_message = await persisted_message_future
            message_was_persisted = True
            yield _sse_event(
                {
                    "type": "user_message",
                    "message": learner_view(persisted_message).model_dump(mode="json"),
                }
            )
            yield _sse_event(
                {
                    "type": "status",
                    "stage": "generating",
                    "message": "正在整理史料與回覆…",
                }
            )

            # LLM 仍在生成時定期送出狀態，避免畫面看起來像停止回應。
            while not chat_task.done():
                completed, _ = await asyncio.wait({chat_task}, timeout=2.0)
                if completed:
                    break
                yield _sse_event(
                    {
                        "type": "status",
                        "stage": "generating",
                        "message": "仍在整理脈絡，請稍候…",
                    }
                )

            response = await chat_task
            yield _sse_event(
                {
                    "type": "status",
                    "stage": "streaming",
                    "message": "回覆已通過檢查，正在顯示…",
                }
            )
            for chunk in _response_chunks(response.response):
                yield _sse_event({"type": "delta", "content": chunk})
                await asyncio.sleep(0)
            yield _sse_event(
                {
                    "type": "complete",
                    "response": learner_view(response).model_dump(mode="json"),
                }
            )
        except HTTPException as exc:
            yield _sse_event(
                {
                    "type": "error",
                    "detail": str(exc.detail),
                    "retryable": exc.status_code >= 500,
                }
            )
        except Exception:
            yield _sse_event(
                {
                    "type": "error",
                    "detail": (
                        "AI 回覆失敗，但你的訊息已保留。"
                        if message_was_persisted
                        else "聊天請求失敗，訊息尚未保存。"
                    ),
                    "retryable": True,
                }
            )
        finally:
            if not persisted_message_future.done():
                persisted_message_future.cancel()
            # 瀏覽器中途離線時仍讓後端完成生成與持久化。
            if not chat_task.done():
                chat_task.add_done_callback(_consume_task_result)

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
        },
    )
