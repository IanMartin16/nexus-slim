# nexus-slim

Motor de presentación **stateless**. Puente `widget → evi-gateway → MCPOne`.
Reemplazo del monolito Spring Boot de Nexus.

> Diseño completo: ver `nexus-slim-diseno.md`. Este README es solo el arranque.

## Qué es (y qué no)

- **Es:** la capa de presentación. Inyecta la persona, mapea el resultado neutral
  de MCPOne al contrato del widget (`sections`) y multiplexa el SSE.
- **No es:** el cerebro. No razona, no elige providers, no calcula inteligencia,
  no guarda memoria. Eso vive en MCPOne (+ SSC). CryptoLink es fuente de verdad.
- **Sin BD.** Stateless de estado persistente. El único estado es el stream vivo.

## Estructura

```
app/
  main.py              # FastAPI + lifespan (cliente httpx) + CORS
  config.py            # settings NEXUS_*
  routers/
    chat.py            # POST /chat -> StreamingResponse (SSE)
    health.py          # /health, /ready (Railway)
  core/
    contract.py        # << la frontera: NeutralResult (kind) y Section (type)
    format.py          # fmt_pct, fmt_money, fmt_confidence, short_iso, tone
    mappers.py         # kind -> sections (3 formas + fallback)
    composer.py        # multiplex SSE (token / data / done)
    persona.py         # system_context estático
    sse.py             # serialización event-stream
  clients/
    mcpone.py          # cliente del cerebro (vía gateway) + modo mock
scripts/
  smoke.py             # prueba el multiplex sin servidor ni MCPOne
```

## Correr local (con cerebro mock)

```bash
pip install -e .            # o instalar las deps del pyproject
export NEXUS_MOCK_BRAIN=true
uvicorn app.main:app --reload
# en otra terminal:
curl -N -X POST localhost:8000/chat -H 'Content-Type: application/json' \
  -d '{"message":"¿cómo está el mercado?"}'
```

O sin levantar servidor:

```bash
NEXUS_MOCK_BRAIN=true python -m scripts.smoke
```

## Contrato SSE (widget ← nexus-slim)

```
event: token   data: {"delta": "..."}            # narrativa del LLM, en vivo
event: data    data: {"sections": [...]}          # KPIs/charts/notices (puede repetirse)
event: done    data: {"ok": true, "summary": ...}
event: error   data: {"code": "...", "message": "..."}
```

## Pendiente / decisiones abiertas

- Protocolo de streaming real de MCPOne (`mcpone._stream_real` es el punto de extensión).
- Formato exacto del discriminador `kind` y de `data` por kind (hoy tolerante).
- Fuente de los labels/locale de los KPI (default inglés v4; el cerebro puede sobreescribir).
- El gateway (Rust) debe hacer **passthrough de streaming**, no acumular la respuesta.
 