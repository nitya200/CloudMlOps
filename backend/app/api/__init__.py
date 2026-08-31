"""Presentation boundary: HTTP routers.

Routers stay thin - they validate input, delegate to a service and map the
result to a response schema.
"""

from fastapi import APIRouter

from app.api import admin, auth, documents, feedback, history, summaries

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(documents.router)
api_router.include_router(summaries.router)
api_router.include_router(history.router)
api_router.include_router(feedback.router)
api_router.include_router(admin.router)

__all__ = ["api_router"]
