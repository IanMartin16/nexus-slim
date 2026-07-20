"""
sse.py — serialización al formato text/event-stream.

Cuatro tipos de evento (ver contract.py):
  token -> delta de narrativa del LLM
  data  -> sections estructuradas (puede emitirse varias veces; el widget concatena)
  done  -> fin de turno
  error -> error en el flujo
"""

from __future__ import annotations

import json

from pydantic import BaseModel


def _frame(event: str, payload: BaseModel) -> bytes:
    data = json.dumps(payload.model_dump(exclude_none=True), ensure_ascii=False)
    return f"event: {event}\ndata: {data}\n\n".encode("utf-8")


def token(ev) -> bytes:   # TokenEvent
    return _frame("token", ev)


def data(ev) -> bytes:    # DataEvent
    return _frame("data", ev)


def done(ev) -> bytes:    # DoneEvent
    return _frame("done", ev)


def error(ev) -> bytes:   # ErrorEvent
    return _frame("error", ev)
