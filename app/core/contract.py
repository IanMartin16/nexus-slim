"""
contract.py — la frontera entre cerebro y presentación.

Dos lados, dos uniones etiquetadas (tagged unions):

  ENTRADA  (lo que MCPOne emite)  -> NeutralResult, discriminado por `kind`
  SALIDA   (lo que el widget renderiza) -> Section, discriminado por `type`

Regla del seam (ver doc, secciones 7 y 11):
  - `kind` es SEMÁNTICO (momentum, regime, trends...), = capability id del
    registry de MCPOne. El cerebro NO sabe cómo se ve; etiqueta con lo que es.
  - El motor traduce semántica -> forma de widget en mappers.py.
  - El motor NO traduce idioma ni inventa datos: las etiquetas de display
    (`label`) y la narrativa las provee el cerebro (locale-aware). El motor
    solo formatea números/fechas y mapea dirección -> tono (color). Locale-neutral.

Los `Section` types salen directo del render real (screenshots v4):
  notice, kpi_grid, text, chart.
Este archivo es la fuente de verdad de qué sabe renderizar el widget.
Si un render existe en el portal y no está aquí, el contrato está incompleto.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# ENTRADA — resultado neutral que emite MCPOne (vía gateway)
# ---------------------------------------------------------------------------


class NeutralMeta(BaseModel):
    """Procedencia del dato. Refleja lo que ya trae CryptoLink v4."""

    source: str | None = None          # p.ej. "internal-analysis"
    as_of: str | None = None           # ts ISO del backend
    fiat: str = "USD"                  # v4: ya alineado a USD desde el motor de Crypto


class NeutralResult(BaseModel):
    """
    Un bloque de resultado estructurado, neutral respecto al widget.

    `kind`  -> discriminador semántico (capability id del registry de MCPOne).
    `data`  -> forma dependiente del kind. Convención esperada:
                 - kinds por-símbolo (momentum, trends): data = {"rows": [...]}
                 - kinds agregados (regime, market_health): data = {state, score, ...}
                 - kinds de flags (risk_flags, anomalies): data = {"rows": [...]}
               (Formato exacto = decisión abierta del doc; aquí es tolerante.)
    `meta`  -> procedencia.
    """

    kind: str
    data: dict[str, Any] = Field(default_factory=dict)
    meta: NeutralMeta = Field(default_factory=NeutralMeta)


# ---------------------------------------------------------------------------
# SALIDA — sections que el widget sabe renderizar (de los screenshots v4)
# ---------------------------------------------------------------------------


Tone = Literal["up", "down", "neutral"]


class KpiItem(BaseModel):
    label: str                         # texto izquierdo del KPI (p.ej. "BTC", "State")
    value: str                         # valor grande (p.ej. "STRONG", "Bullish", "0.97")
    unit: str = ""                     # sufijo/contexto (p.ej. "+2.30%")
    tone: Tone = "neutral"             # gobierna el color (verde/coral/gris)


class KpiGridSection(BaseModel):
    type: Literal["kpi_grid"] = "kpi_grid"
    id: str
    title: str
    items: list[KpiItem] = Field(default_factory=list)


class TextSection(BaseModel):
    type: Literal["text"] = "text"
    id: str
    title: str | None = None
    text: str


class NoticeSection(BaseModel):
    type: Literal["notice"] = "notice"
    id: str
    level: Literal["info", "warning", "error"] = "info"
    text: str
    meta: str | None = None            # línea fina: "asOf=... · source=... · fiat=..."


class ChartPoint(BaseModel):
    v: float
    t: str | None = None               # timestamp opcional del punto


class ChartSeries(BaseModel):
    symbol: str
    last: float | None = None
    points: list[float] = Field(default_factory=list)  # sparkline (imagen 2: tendencia)


class ChartSection(BaseModel):
    type: Literal["chart"] = "chart"
    id: str
    title: str
    series: list[ChartSeries] = Field(default_factory=list)


# Unión discriminada por `type` — espejo exacto del patrón de `kind` en la entrada.
Section = Annotated[
    Union[KpiGridSection, TextSection, NoticeSection, ChartSection],
    Field(discriminator="type"),
]


# ---------------------------------------------------------------------------
# Eventos SSE (widget <- nexus-slim). Dos carriles paralelos:
#   token  -> narrativa del LLM (agnóstica de kind, es prosa)
#   data   -> sections estructuradas (gobernadas por kind)
# ---------------------------------------------------------------------------


class TokenEvent(BaseModel):
    delta: str


class DataEvent(BaseModel):
    sections: list[Section] = Field(default_factory=list)


class DoneEvent(BaseModel):
    ok: bool = True
    summary: str | None = None


class ErrorEvent(BaseModel):
    code: str
    message: str
