"""
mappers.py — semántica (kind) -> forma de widget (sections).

Aquí ocurre el colapso de N handlers a ~3 formas genéricas. La tabla MAPPERS
ES el conocimiento de presentación: vive en el motor, NO en el cerebro.

  map_symbol_kpis   -> momentum, trends      (lista de KPIs por símbolo + chart)
  map_aggregate_kpi -> regime, market_health (KPI agregado único)
  map_flag_list     -> risk_flags, anomalies (lista de flags)
  map_fallback      -> kind desconocido      (notice; la narrativa la lleva el LLM)

El fallback es lo que permite despliegue independiente: MCPOne puede lanzar una
capability nueva y el motor la alcanza después, sin coordinar releases (Lego).
"""

from __future__ import annotations

from typing import Callable

from . import format as fmt
from .contract import (
    ChartSection,
    ChartSeries,
    KpiGridSection,
    KpiItem,
    NeutralResult,
    NoticeSection,
    Section,
    TextSection,
)

# Títulos estructurales (microcopy del shell). Default en inglés por el pivote
# internacional v4; el cerebro puede sobreescribir con `data["title"]` si hay locale.
TITLES = {
    "momentum": "Momentum",
    "trends": "Market Trends",
    "regime": "Market Regime",
    "market_health": "Market Health",
    "risk_flags": "Risk Flags",
    "anomalies": "Anomalies",
    "social_pulse": "Social Pulse",
    "prices": "Prices",
    "movers": "Top Movers",
    "snapshot": "Market Snapshot",
}

# Labels de KPI agregado. Mismo criterio: default inglés, override del cerebro.
AGG_LABELS = {"state": "State", "confidence": "Confidence", "score": "Score"}


def _notice(result: NeutralResult) -> NoticeSection:
    m = result.meta
    meta_line = f"asOf={fmt.short_iso(m.as_of)} · source={m.source} · fiat={m.fiat}"
    title = TITLES.get(result.kind, result.kind)
    return NoticeSection(
        id=f"sec_notice_{result.kind}",
        level="info",
        text=f"{title} retrieved from CryptoLink.",
        meta=meta_line,
    )


def _title(result: NeutralResult) -> str:
    return result.data.get("title") or TITLES.get(result.kind, result.kind)


def _empty_state(result: NeutralResult) -> list[Section]:
    """rows vacío: en vez de un grid hueco, muestra el summary de CryptoLink
    como texto. CryptoLink ya manda un mensaje amable ('No relevant alerts...')."""
    summary = result.data.get("summary")
    text = summary or f"No {TITLES.get(result.kind, result.kind).lower()} to report right now."
    return [
        _notice(result),
        TextSection(id=f"sec_text_{result.kind}", title=_title(result), text=text),
    ]


def map_symbol_kpis(result: NeutralResult) -> list[Section]:
    """momentum / trends: KPI por símbolo; trends añade chart si hay `points`."""
    rows = result.data.get("rows", []) or []
    if not rows:
        return _empty_state(result)
    items: list[KpiItem] = []
    for row in rows[:3]:
        direction = row.get("direction", "")
        # momentum -> strength; trends -> direction. `label` del cerebro gana.
        raw = row.get("strength") or row.get("direction") or ""
        value = row.get("label") or str(raw).upper()
        items.append(
            KpiItem(
                label=str(row.get("symbol", "")),
                value=value,
                unit=fmt.fmt_pct(row.get("changePct")),
                tone=fmt.tone_from_direction(direction),
            )
        )

    sections: list[Section] = [
        _notice(result),
        KpiGridSection(id=f"sec_kpis_{result.kind}", title=_title(result), items=items),
    ]

    # Chart (imagen 2: "Tendencia reciente"). Solo si el backend manda series.
    series = [
        ChartSeries(
            symbol=str(r.get("symbol", "")),
            last=fmt._to_float(r.get("last")),
            points=[p for p in (r.get("points") or []) if isinstance(p, (int, float))],
        )
        for r in rows
        if r.get("points")
    ]
    if series:
        sections.append(
            ChartSection(id=f"sec_chart_{result.kind}", title="Recent trend", series=series)
        )
    return sections


def map_aggregate_kpi(result: NeutralResult) -> list[Section]:
    """regime / market_health: KPI agregado. Solo incluye los campos presentes
    (market_health no trae confidence; regime sí) — sin tarjetas vacías."""
    d = result.data
    state = str(d.get("state", ""))
    tone = fmt.tone_from_state(state)
    items: list[KpiItem] = []

    if d.get("state") is not None:
        items.append(
            KpiItem(label=AGG_LABELS["state"], value=d.get("state_label") or state.upper(), tone=tone)
        )
    if d.get("confidence") is not None:
        items.append(
            KpiItem(label=AGG_LABELS["confidence"], value=fmt.fmt_confidence(d.get("confidence")), tone=tone)
        )
    if d.get("score") is not None:
        items.append(
            KpiItem(label=AGG_LABELS["score"], value=str(d.get("score")), tone=tone)
        )

    sections: list[Section] = [
        _notice(result),
        KpiGridSection(id=f"sec_kpis_{result.kind}", title=_title(result), items=items),
    ]
    # Si el agregado trae summary, muéstralo como contexto legible.
    if d.get("summary"):
        sections.append(
            TextSection(id=f"sec_text_{result.kind}", title="Read", text=str(d["summary"]))
        )
    return sections


def map_social_pulse(result: NeutralResult) -> list[Section]:
    """social_pulse: state+score, cualitativos (breadth/conviction/leadership),
    top assets y summary. Forma más rica que un agregado simple."""
    d = result.data
    state = str(d.get("state", ""))
    tone = fmt.tone_from_state(state)

    items: list[KpiItem] = []
    if d.get("state") is not None:
        items.append(KpiItem(label="State", value=state.upper(), tone=tone))
    if d.get("score") is not None:
        items.append(KpiItem(label="Score", value=str(d.get("score")), tone=tone))
    for field in ("breadth", "conviction", "leadership"):
        if d.get(field):
            items.append(
                KpiItem(label=field.capitalize(), value=str(d[field]).capitalize(), tone=tone)
            )
    if d.get("topAssets"):
        items.append(KpiItem(label="Top assets", value=", ".join(d["topAssets"]), tone=tone))

    sections: list[Section] = [
        _notice(result),
        KpiGridSection(id=f"sec_kpis_{result.kind}", title=_title(result), items=items),
    ]
    if d.get("summary"):
        sections.append(
            TextSection(id=f"sec_text_{result.kind}", title="Narrative", text=str(d["summary"]))
        )
    return sections


def map_flag_list(result: NeutralResult) -> list[Section]:
    """risk_flags / anomalies: lista de alertas."""
    flags = result.data.get("rows", []) or []
    if not flags:
        # Sin alertas: muestra el summary amable de CryptoLink, no un grid vacío.
        return _empty_state(result)
    items = [
        KpiItem(
            label=str(f.get("symbol") or f.get("title") or f.get("label", "")),
            value=f.get("label") or str(f.get("severity") or f.get("level", "")).upper(),
            unit=str(f.get("detail") or f.get("note", "")),
            tone="down" if str(f.get("severity") or f.get("level", "")).lower() in ("high", "critical") else "neutral",
        )
        for f in flags[:6]
    ]
    return [
        _notice(result),
        KpiGridSection(id=f"sec_flags_{result.kind}", title=_title(result), items=items),
    ]


def map_prices(result: NeutralResult) -> list[Section]:
    rows = result.data.get("rows", []) or []
    if not rows:
        return _empty_state(result)
    fiat = result.meta.fiat or "USD"
    items = []
    for r in rows[:8]:
        symbol = str(r.get("symbol", ""))
        price = r.get("price")
        change = r.get("change24h")
        # unit lleva el fiat; si hay cambio 24h, se muestra como contexto
        unit = fiat
        tone = "neutral"
        if change is not None:
            tone = "up" if change >= 0 else "down"
            unit = f"{fiat}  ({change:+.2f}% 24h)"
        items.append(KpiItem(
            label=symbol,
            value=fmt.fmt_money(price),
            unit=unit,
            tone=tone,
        ))
    return [
        _notice(result),
        KpiGridSection(id=f"sec_kpis_{result.kind}", title=_title(result), items=items),
    ]


def map_movers(result: NeutralResult) -> list[Section]:
    """movers: rows con symbol/direction/changePct/last. Como símbolos pero
    mostrando el % de cambio y el precio."""
    rows = result.data.get("rows", []) or []
    if not rows:
        return _empty_state(result)
    fiat = result.meta.fiat or "USD"
    items = [
        KpiItem(
            label=str(r.get("symbol", "")),
            value=fmt.fmt_pct(r.get("changePct")),
            unit=fmt.fmt_money(r.get("last")) + f" {fiat}" if r.get("last") is not None else "",
            tone=fmt.tone_from_direction(str(r.get("direction", ""))),
        )
        for r in rows[:6]
    ]
    return [
        _notice(result),
        KpiGridSection(id=f"sec_kpis_{result.kind}", title=_title(result), items=items),
    ]


def map_snapshot(result: NeutralResult) -> list[Section]:
    """snapshot: marketMood + precios principales. Los metadatos (source/asOf)
    vienen DENTRO del data, no en meta (por la forma cruda de snapshot)."""
    d = result.data
    fiat = d.get("fiat") or result.meta.fiat or "USD"
    mood = str(d.get("marketMood", ""))
    prices = d.get("prices", {}) or {}

    items: list[KpiItem] = []
    if mood:
        items.append(KpiItem(label="Mood", value=mood.capitalize(), tone="neutral"))
    for sym, price in prices.items():
        if isinstance(price, (int, float)):
            items.append(KpiItem(label=str(sym), value=fmt.fmt_money(price), unit=fiat, tone="neutral"))

    # notice con los metadatos que snapshot trae dentro del data.
    notice = NoticeSection(
        id=f"sec_notice_{result.kind}",
        level="info",
        text=f"{_title(result)} retrieved from CryptoLink.",
        meta=f"asOf={fmt.short_iso(d.get('asOf'))} · source={d.get('source')} · fiat={fiat}",
    )
    return [
        notice,
        KpiGridSection(id=f"sec_kpis_{result.kind}", title=_title(result), items=items),
    ]


def map_fallback(result: NeutralResult) -> list[Section]:
    """kind desconocido: degrada con gracia. La narrativa la cubre el LLM (tokens)."""
    return [
        NoticeSection(
            id=f"sec_notice_{result.kind}",
            level="info",
            text=f"Result '{result.kind}' received.",
            meta=f"source={result.meta.source} · asOf={fmt.short_iso(result.meta.as_of)}",
        )
    ]


def map_error(result: NeutralResult) -> list[Section]:
    """kind '_error': la ejecución falló. Notice honesto, no un mensaje engañoso."""
    failed_kind = result.data.get("kind", "data")
    title = TITLES.get(failed_kind, failed_kind)
    return [
        NoticeSection(
            id=f"sec_notice_error_{failed_kind}",
            level="warning",
            text=f"{title} is not available right now. Please try again shortly.",
            meta=None,
        )
    ]


MAPPERS: dict[str, Callable[[NeutralResult], list[Section]]] = {
    "momentum": map_symbol_kpis,
    "trends": map_symbol_kpis,
    "regime": map_aggregate_kpi,
    "market_health": map_aggregate_kpi,
    "risk_flags": map_flag_list,
    "anomalies": map_flag_list,
    "social_pulse": map_social_pulse,
    "prices": map_prices,
    "movers": map_movers,
    "snapshot": map_snapshot,
    "_error": map_error,
}


def to_sections(result: NeutralResult) -> list[Section]:
    """Despacha por kind. kind no mapeado -> fallback (Lego: deploy independiente)."""
    mapper = MAPPERS.get(result.kind, map_fallback)
    return mapper(result)
