"""chat.py — el endpoint de cara al widget. POST /chat -> SSE."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..core import composer

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    # session_id es un HANDLE que se pasa al cerebro; el motor no lo persiste.
    session_id: str | None = None


# Headers para que el SSE no se quede buffereado en proxies intermedios.
# El gateway (Rust) también debe hacer passthrough de streaming, no acumular.
_SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


@router.post("/chat")
async def chat(req: ChatRequest, request: Request) -> StreamingResponse:
    brain = request.app.state.brain
    session_id = req.session_id or f"sess_{uuid.uuid4().hex[:12]}"
    return StreamingResponse(
        composer.stream_chat(brain, req.message, session_id),
        media_type="text/event-stream",
        headers=_SSE_HEADERS,
    )
