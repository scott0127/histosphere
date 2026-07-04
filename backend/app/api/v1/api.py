from fastapi import APIRouter

from app.api.v1.endpoints import admin, chat, conditions, conversations, events, participants, personas, sessions, stats, tasks

api_router = APIRouter()
api_router.include_router(admin.router)
api_router.include_router(events.router)
api_router.include_router(conditions.router)
api_router.include_router(conversations.router)
api_router.include_router(chat.router)
api_router.include_router(participants.router)
api_router.include_router(personas.router)
api_router.include_router(sessions.router)
api_router.include_router(stats.router)
api_router.include_router(tasks.router)
