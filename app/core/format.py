"""
format.py — utilidades de presentación que SOBREVIVEN al motor.

Son las únicas piezas de la vieja librería de helpers que se quedan:
formato de números/fechas (locale-neutral) y mapeo semántico -> tono (color).

Lo que NO está aquí (a propósito): esRegimeState / esStrength / esDirection.
Esos eran traductores de idioma — desaparecen. La traducción de valores de
datos a texto de display la provee el cerebro (label locale-aware); la
narrativa la genera el LLM. El motor no traduce idioma.

`tone_from_*` NO es traducción: es semántica -> color (up/down/neutral),
locale-neutral, y por eso sí vive aquí.
"""

from __future__ import annotations

from typing import Any

from .contract import Tone


def _to_float(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def fmt_pct(v: Any) -> str:
    """2.3 -> '+2.30%'. None/no-parseable -> ''."""
    f = _to_float(v)
    if f is None:
        return ""
    return f"{f:+.2f}%"


def fmt_money(value) -> str:
    n = _to_float(value)
    if n is None:
        return "—"
    a = abs(n)
    if a >= 1:
        decimals = 2
    elif a >= 0.01:
        decimals = 4
    else:
        decimals = 8
    # separador de miles + decimales adaptativos; recorta ceros sobrantes
    # solo en el tramo de muchos decimales para no ensuciar (< $0.01).
    s = f"{n:,.{decimals}f}"
    if decimals == 8:
        s = s.rstrip("0").rstrip(".")  # 0.00001520 -> 0.0000152
    return s


def fmt_confidence(v: Any) -> str:
    """0.64 -> '64%'; 64 -> '64%'. None -> ''."""
    f = _to_float(v)
    if f is None:
        return ""
    pct = f * 100 if f <= 1 else f
    return f"{round(pct)}%"


def short_iso(ts: Any) -> str:
    """'2026-03-09T20:16:00Z' -> '2026-03-09 20:16'. Tolerante a basura."""
    if not ts:
        return ""
    s = str(ts).replace("T", " ")
    return s[:16]


def tone_from_direction(direction: Any) -> Tone:
    d = str(direction).lower()
    if d == "up":
        return "up"
    if d == "down":
        return "down"
    return "neutral"


def tone_from_state(state: Any) -> Tone:
    s = str(state).lower()
    if "bull" in s:
        return "up"
    if "bear" in s:
        return "down"
    return "neutral"
