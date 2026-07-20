"""
mcpone.py — cliente del cerebro.

Nexus-slim NO razona: delega a MCPOne (vía evi-gateway). Este cliente abre un
stream y entrega `BrainEvent`s al composer:

  BrainToken      -> delta de narrativa (del LLM)
  BrainStructured -> un NeutralResult (bloque estructurado, discriminado por kind)

`session_id` se PASA, no se guarda: la memoria vive en MCPOne (+ SSC). El motor
es stateless.

Modo mock (NEXUS_MOCK_BRAIN=true): emite una secuencia canónica para desarrollar
el motor y el widget sin MCPOne todavía. El protocolo real de streaming de MCPOne
es decisión abierta (ver doc); `_stream_real` marca el punto de extensión.
"""

from __future__ import annotations

import asyncio
import json
from typing import AsyncIterator, Literal, Union

import httpx
from pydantic import BaseModel, Field

from ..config import Settings
from ..core.contract import NeutralResult


class BrainToken(BaseModel):
    type: Literal["token"] = "token"
    delta: str


class BrainStructured(BaseModel):
    type: Literal["structured"] = "structured"
    result: NeutralResult


BrainEvent = Union[BrainToken, BrainStructured]


class MCPOneClient:
    def __init__(self, http: httpx.AsyncClient, settings: Settings):
        self._http = http
        self._s = settings

    async def stream(
        self, message: str, session_id: str, system_context: str
    ) -> AsyncIterator[BrainEvent]:
        if self._s.mock_brain:
            async for ev in _stream_mock(message):
                yield ev
            return
        async for ev in self._stream_real(message, session_id, system_context):
            yield ev

    async def _stream_real(
        self, message: str, session_id: str, system_context: str
    ) -> AsyncIterator[BrainEvent]:
        """
        Llama a MCPOne A TRAVÉS del evi-gateway.

        El gateway NO es passthrough puro: expone un único endpoint de proxy
        (`/api/proxy`) que espera un sobre {route, payload} y valida headers.
        El body real de MCPOne (user_input, client_context) va DENTRO de payload.

        Transporte requerido por el gateway:
          - path:   /api/proxy
          - header: X-API-Key      (credencial)
          - header: X-Request-ID   (id de la petición)
          - body:   {"route": "mcpone.execute", "payload": {...}}

        La respuesta del gateway envuelve la de MCPOne; se desenvuelve abajo.
        """
        url = f"{self._s.gateway_url}{self._s.gateway_proxy_path}"
        headers = {
            "X-API-Key": self._s.gateway_api_key,
            "X-Request-ID": session_id,
        }
        body = {
            "route": self._s.gateway_mcpone_route,
            "payload": {
                "user_input": message,
                "client_context": {"source": "nexus-slim", "channel": "widget"},
            },
        }
        resp = await self._http.post(
            url, json=body, headers=headers, timeout=self._s.request_timeout_s
        )
        resp.raise_for_status()
        payload = _unwrap_gateway(resp.json())

        tool_result = payload.get("tool_result")

        if tool_result and tool_result.get("ok") is True:
            narrative = tool_result.get("narrative")
            if narrative:
                yield BrainToken(delta=narrative)
            # Hubo ejecución exitosa: bloque estructurado neutral. Ignora user_facing.
            yield BrainStructured(result=NeutralResult(
                kind=tool_result.get("kind", "unknown"),
                data=tool_result.get("data") or {},
                meta={
                    "source": tool_result.get("source"),
                    "as_of": tool_result.get("as_of"),
                    "fiat": tool_result.get("fiat", "USD"),
                },
            ))
            return                      # <── FIX: no caer al bloque de recomendación

        if tool_result is not None:
            # Ejecución falló (CryptoLink caído, timeout...). Di la verdad.
            yield BrainStructured(
                result=NeutralResult(
                    kind="_error",
                    data={
                        "kind": tool_result.get("kind", "unknown"),
                        "error": tool_result.get("error") or "unavailable",
                    },
                    meta={"source": tool_result.get("source")},
                )
            )
            return

        # No hubo tool_result: recomendación pura. Usa el user_facing como texto.
        text = _user_facing_text(payload)
        if text:
            yield BrainToken(delta=text)


def _user_facing_text(payload: dict) -> str:
    """Compone un texto legible desde los campos user_facing de recomendación."""
    capability = payload.get("capability_name")
    
    capability_line = f"Capacidad principal: {capability}"  if capability else None

    parts = [
        payload.get("user_facing_title"),
        payload.get("user_facing_summary"),
        capability_line,
        payload.get("user_facing_context"),
        payload.get("next_step_hint"),
    ]
    return "\n\n".join(p for p in parts if p)


def _unwrap_gateway(body: dict) -> dict:
    """
    El evi-gateway envuelve la respuesta de MCPOne en un sobre:
        {"request_id","route","status", "data": {...respuesta real de MCPOne...}}

    Se destapa PRIMERO el sobre del gateway (su marca es status/route + data),
    y solo si no hay sobre se asume respuesta directa. El orden importa: el sobre
    del gateway también trae `request_id` en la raíz, así que no se puede usar esa
    llave para decidir "es directo" (fue el bug del turno vacío).
    """
    if not isinstance(body, dict):
        return {}

    # 1) Sobre del gateway: tiene metadata de proxy (route/status) + data anidado.
    if ("route" in body or "status" in body) and isinstance(body.get("data"), dict):
        return body["data"]

    # 2) Otras envolturas conocidas.
    for key in ("data", "result", "payload", "response"):
        inner = body.get(key)
        if isinstance(inner, dict) and ("tool_result" in inner or "user_facing_title" in inner):
            return inner

    # 3) Ya es la respuesta de MCPOne directa (sin gateway).
    return body


# ---------------------------------------------------------------------------
# Modo mock — secuencia canónica para desarrollo (regime + trends + narrativa)
# ---------------------------------------------------------------------------


async def _stream_mock(message: str) -> AsyncIterator[BrainEvent]:
    # 1) bloque estructurado: regime (mapea a KPI agregado)
    yield BrainStructured(
        result=NeutralResult(
            kind="regime",
            data={
                "state": "bull",
                "score": 0.97,
                "confidence": 0.64,
                "summary": "Momentum and trends favor a constructive read.",
            },
            meta={"source": "internal-analysis", "as_of": "2026-03-09T20:16:00Z", "fiat": "USD"},
        )
    )
    # 2) bloque estructurado: trends (KPI por símbolo + chart con points)
    yield BrainStructured(
        result=NeutralResult(
            kind="trends",
            data={
                "rows": [
                    {"symbol": "BTC", "direction": "down", "changePct": -1.8, "last": 60500.12,
                     "points": [62000, 61800, 61750, 61700, 62100, 61900, 60500]},
                    {"symbol": "ETH", "direction": "down", "changePct": -2.1, "last": 1762.40,
                     "points": [1810, 1805, 1804, 1803, 1820, 1812, 1762]},
                    {"symbol": "SOL", "direction": "neutral", "changePct": 0.3, "last": 75.15,
                     "points": [82, 76, 75, 75, 75, 75, 75.15]},
                ]
            },
            meta={"source": "cryptolink-api-v2", "as_of": "2026-03-09T20:16:00Z", "fiat": "USD"},
        )
    )
    # 3) narrativa del LLM (carril token) — llega entrelazada/después
    for chunk in [
        "El mercado ", "muestra un régimen ", "constructivo. ",
        "Las tres principales ", "ceden algo de terreno ", "en el corto plazo.",
    ]:
        await asyncio.sleep(0.02)
        yield BrainToken(delta=chunk)
