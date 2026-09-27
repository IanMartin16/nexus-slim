# Despliegue a Prod — evi-gateway + nexus-slim (Fase 2)

Topología real:
- Railway: proyectos INDEPENDIENTES que se hablan por URLs públicas (patrón actual).
- Portal evilink.dev: Vercel (le habla a nexus-slim por URL pública).
- MCPOne: ya en prod (público — Nexus core lo consume así; se mantiene).
- Red privada: NO aplica hoy (proyectos separados). Anotada como mejora
  post-decomiso (consolidar en un proyecto + cerrar exposición pública de MCPOne).

Orden: de adentro hacia afuera — MCPOne (update) → gateway → nexus-slim → portal.
Cada paso se VERIFICA antes del siguiente. El tráfico real no se mueve hasta el
canary (Paso 5), que es reversible con una env.

═══════════════════════════════════════════════════════════════════
PASO 0 — nexus-slim a GitHub
═══════════════════════════════════════════════════════════════════
- [ ] Verificar `.env` en `.gitignore` ANTES del primer commit
      (el .env tiene gateway_api_key; si sube, queda en el historial para siempre)
- [ ] Crear `.env.example` (sin valores):
        GATEWAY_URL=
        GATEWAY_PROXY_PATH=/api/proxy
        GATEWAY_API_KEY=
        GATEWAY_MCPONE_ROUTE=mcpone.execute
        NEXUS_MOCK_BRAIN=false
- [ ] requirements.txt completo (fastapi, uvicorn, httpx, pydantic-settings...)
- [ ] Push a GitHub

═══════════════════════════════════════════════════════════════════
PASO 1 — MCPOne: update a la versión con ejecución (deploy seguro)
═══════════════════════════════════════════════════════════════════
La versión en prod NO tiene la capa de ejecución ni los providers. Se actualiza
ANTES que el resto. Es seguro: Nexus core usa los flujos de recomendación, que
no cambiaron; lo nuevo (ejecución, narrativa) queda dormido hasta que alguien
lo llame.

- [ ] Push del MCPOne local (execution layer + capabilities + providers) a su repo
- [ ] Envs nuevas en Railway (proyecto MCPOne):
        ENABLE_PROVIDER_ENRICHMENT=false     <- narrativa APAGADA (estrategia)
        ACTIVE_PROVIDER=none                 <- doble seguro
        OPENAI_API_KEY=<key>                 <- listas para el futuro switch
        ANTHROPIC_API_KEY=<key>
        OPENAI_MODEL=gpt-4.1-mini
        ANTHROPIC_MODEL=claude-haiku-4-5
- [ ] Deploy y verificar:
        curl POST <mcpone-prod>/orchestrate  con "give me momentum of BTC"
        -> debe traer tool_result poblado (la ejecución viva en prod)
        -> narrative debe venir null (flag apagado) ✓
- [ ] Verificar que Nexus core sigue funcionando (el widget en prod responde
      recomendaciones igual que siempre — los flujos viejos intactos)

═══════════════════════════════════════════════════════════════════
PASO 2 — evi-gateway: nuevo proyecto en Railway
═══════════════════════════════════════════════════════════════════
- [ ] Nuevo proyecto Railway desde el repo GitHub del gateway
      (detecta el Dockerfile -> build de la imagen Rust tal cual)
- [ ] GENERAR API KEY DE PROD (nueva, no la dev):
        openssl rand -hex 32     (o similar; larga y aleatoria)
      La nexus_dev_key circuló en pruebas/documentos — la de prod nace limpia.
- [ ] Envs (proyecto gateway):
        HOST=0.0.0.0
        APP_ENV=production
        MCPONE_URL=<URL pública de MCPOne en prod>
        DEFAULT_TIMEOUT_MS=8000              <- ver nota timeout abajo
        EVIGATE_API_KEYS=nexus:<KEY_PROD>:mcpone.execute
      (PORT lo inyecta Railway; confirmar que el binario lee $PORT del entorno)
      Nota scope: SOLO mcpone.execute — mínimo privilegio. Los scopes de
      health/registry/metrics se agregan si algún cliente los necesita.
      Nota timeout: en local CryptoLink llegó a tardar ~9s (social_pulse
      latency_ms=9217). Con 5000ms el gateway cortaría antes. 8000-10000ms
      da margen; ajustar según se observe en prod.
- [ ] VERIFICAR:
        curl https://<gateway-prod>/api/health
        -> "operational", upstream mcpone "operational" con latencia
        Si upstream degraded: MCPONE_URL mal — arreglar ANTES de seguir.
- [ ] VERIFICAR el proxy con la key nueva:
        curl POST https://<gateway-prod>/api/proxy
          -H "X-API-Key: <KEY_PROD>"
          body: {"route":"mcpone.execute","payload":{"user_input":"momentum of BTC",...}}
        -> respuesta envuelta {request_id, route, status:200, data:{...tool_result...}}

═══════════════════════════════════════════════════════════════════
PASO 3 — nexus-slim: nuevo proyecto en Railway
═══════════════════════════════════════════════════════════════════
- [ ] Nuevo proyecto Railway desde el repo GitHub de nexus-slim (Nixpacks/Python)
- [ ] Start command (respeta el $PORT que Railway inyecta; NO tocar código):
        uvicorn app.main:app --host 0.0.0.0 --port $PORT
      (0.0.0.0 basta: el portal en Vercel le habla por la URL pública IPv4)
- [ ] Envs (proyecto nexus-slim):
        GATEWAY_URL=https://<gateway-prod>
        GATEWAY_PROXY_PATH=/api/proxy
        GATEWAY_API_KEY=<KEY_PROD del paso 2>
        GATEWAY_MCPONE_ROUTE=mcpone.execute
        NEXUS_MOCK_BRAIN=false
- [ ] VERIFICAR la cadena completa en prod:
        curl -N POST https://<nexus-slim-prod>/chat
          body: {"message":"give me momentum of BTC"}
        -> SSE: event data con sections (notice + kpi_grid), done ok:true
        (sin event token: la narrativa está apagada — correcto ✓)
      Este curl valida: slim -> gateway -> MCPOne -> CryptoLink, TODO en prod.

═══════════════════════════════════════════════════════════════════
PASO 4 — Portal (Vercel): conectar sin activar
═══════════════════════════════════════════════════════════════════
- [ ] Push del route unificado con switch (si no se hizo ya — era el push seguro)
- [ ] Envs en Vercel:
        NEXUS_BACKEND=core                    <- explícito; documenta la posición
        NEXUS_SLIM_URL=https://<nexus-slim-prod>
      (NEXUS_API_BASE y NEXUS_WEB_SECRET ya existen — no tocar)
- [ ] Redeploy del portal (Vercel toma las envs en el build)
- [ ] Verificar que el widget en prod sigue normal (está en core — cero cambio)

ESTADO al terminar el Paso 4: todo desplegado y conectado. El tráfico real
sigue en Nexus core. La ruta nueva completa (slim->gateway->MCPOne) vive en
prod, probada por curl, SIN usuarios. Se puede quedar así el tiempo que sea.

═══════════════════════════════════════════════════════════════════
PASO 5 — CANARY (cuando se decida; reversible en segundos)
═══════════════════════════════════════════════════════════════════
- [ ] NEXUS_BACKEND=slim en Vercel (redeploy del portal para tomar la env)
- [ ] Probar el widget en prod: momentum, prices, algo no-crypto (recomendación),
      risk-flags (posible estado vacío)
- [ ] Observar logs: nexus-slim, gateway (proxy_completed), MCPOne (resoluciones)
- [ ] ROLLBACK si algo falla: NEXUS_BACKEND=core (+redeploy) — Nexus core nunca
      murió, vuelve en minutos
- [ ] Nota Vercel: cambiar env requiere redeploy (no es instantáneo como Railway).
      El rollback tarda lo que tarde el redeploy del portal (~1-2 min).
- [ ] Periodo de observación: días/semanas, según confianza. Nexus core VIVO
      todo ese tiempo (el history del widget sigue saliendo de él).

═══════════════════════════════════════════════════════════════════
PASO 6 — DECOMISO (mucho después; lista de lo que destraba)
═══════════════════════════════════════════════════════════════════
Sólo cuando slim sostuvo tráfico real sin incidentes por un periodo largo:
- [ ] pg_dump de la BD de Nexus core (nexus_conversations, nexus_messages)
      — ANTES de eliminar; el seguro de los datos aunque se decida descartar
- [ ] Decidir el hogar del history (SSC / Nexus-memoria) o historial desde cero
- [ ] Eliminar el servicio Nexus core en Railway (esto borra su BD — por eso el dump)
- [ ] Quitar del portal: NEXUS_API_BASE, NEXUS_WEB_SECRET (ya sin uso)
- [ ] ENCENDER LA NARRATIVA: ENABLE_PROVIDER_ENRICHMENT=true +
      ACTIVE_PROVIDER=openai (o anthropic) en MCPOne
- [ ] Mejora post-decomiso (anotada): consolidar gateway+MCPOne(+slim) en un
      proyecto Railway con red privada .railway.internal, y cerrar la
      exposición pública de MCPOne (el gateway como único punto de entrada)

═══════════════════════════════════════════════════════════════════
Resumen de secretos que nacen en este despliegue
═══════════════════════════════════════════════════════════════════
- EVIGATE_API_KEYS (gateway) / GATEWAY_API_KEY (slim): la KEY_PROD nueva — 
  generada para prod, nunca en git, solo en Railway
- OPENAI_API_KEY / ANTHROPIC_API_KEY: en Railway (MCPOne), dormidas tras el flag
- Nada de esto va en archivos del repo; los .env.example documentan sin valores
