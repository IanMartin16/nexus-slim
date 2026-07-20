"""
composer.py — el multiplex SSE. El núcleo del motor.

Consume el stream del cerebro (MCPOne) y emite el SSE del widget en dos carriles:
  - BrainToken      -> event: token   (narrativa, tal cual, en vivo)
  - BrainStructured -> event: data    (sections, mapeadas por kind)
Al cerrar: event: done.

Es order-agnostic: emite lo que llega en el orden en que llega (token o data),
así soporta tanto "estructura primero, narrativa después" como entrelazado, y
multi-kind (varios bloques estructurados en un mismo turno).

Stateless: el único estado es el del stream vivo, en memoria, que muere con el
socket. Nada persistente.
"""

from __future__ import annotations

from typing import AsyncIterator

from ..clients.mcpone import BrainStructured, BrainToken, MCPOneClient
from . import mappers, persona, sse
from .contract import DataEvent, DoneEvent, ErrorEvent, NoticeSection, TokenEvent


async def stream_chat(
    brain: MCPOneClient, message: str, session_id: str
) -> AsyncIterator[bytes]:
    kinds_seen: list[str] = []
    emitted_any = False
    try:
        async for ev in brain.stream(message, session_id, persona.SYSTEM_CONTEXT):
            if isinstance(ev, BrainToken):
                emitted_any = True
                yield sse.token(TokenEvent(delta=ev.delta))
            elif isinstance(ev, BrainStructured):
                emitted_any = True
                kinds_seen.append(ev.result.kind)
                sections = mappers.to_sections(ev.result)
                yield sse.data(DataEvent(sections=sections))
    except Exception as exc:  # noqa: BLE001 — el motor nunca tumba el socket sin avisar
        # Notice legible para el widget (que sí sabe renderizar sections) +
        # error técnico para el cliente/logs. No dejamos al usuario con la nada.
        yield sse.data(DataEvent(sections=[_error_notice()]))
        yield sse.error(ErrorEvent(code="brain_stream_error", message=str(exc)))
        yield sse.done(DoneEvent(ok=False, summary=None))
        return

    # Turno vacío: MCPOne no dio ni ejecución ni texto. No dejamos silencio.
    if not emitted_any:
        yield sse.data(DataEvent(sections=[_empty_notice()]))

    yield sse.done(DoneEvent(ok=True, summary=_summary(kinds_seen)))


def _error_notice() -> NoticeSection:
    return NoticeSection(
        id="sec_notice_stream_error",
        level="warning",
        text="Something went wrong while resolving your request. Please try again.",
    )


def _empty_notice() -> NoticeSection:
    return NoticeSection(
        id="sec_notice_empty",
        level="info",
        text="I couldn't find a clear answer for that. Try rephrasing your question.",
    )


def _summary(kinds: list[str]) -> str | None:
    visible = [k for k in kinds if not k.startswith("_")]
    if not visible:
        return None
    titles = [mappers.TITLES.get(k, k) for k in dict.fromkeys(visible)]
    return " · ".join(titles)
