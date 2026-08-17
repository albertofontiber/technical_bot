# -*- coding: utf-8 -*-
"""Medidor de USO/COSTE de llamadas LLM por observación pura (s324d; nace del replay congelado de s324c).

Envuelve `anthropic.resources.messages.Messages.create` y `openai.resources.chat.completions.Completions.create`
SOLO para leer `usage` de cada respuesta: no altera argumentos ni respuestas ni la vara del juez. La fase la
etiqueta el hilo principal (`METER.phase = "judge"`). Importa los SDK perezosamente en `install()`, así el
módulo se puede importar y testear sin entorno.

Precios USD por millón de tokens con su FUENTE declarada; un modelo sin precio suma tokens pero no dólares
(`usd=None`, `price="DESCONOCIDO"`), nunca se inventa.
"""
from __future__ import annotations

import threading
import time

PRICES_USD_PER_M: dict[str, dict] = {
    "claude-sonnet-4-6": {"in": 3.0, "out": 15.0, "src": "anthropic first-party (skill claude-api)"},
    "claude-sonnet-5": {"in": 3.0, "out": 15.0, "src": "anthropic first-party (skill claude-api; lista)"},
    "claude-haiku-4-5": {"in": 1.0, "out": 5.0, "src": "anthropic first-party (skill claude-api)"},
    "claude-opus-4-8": {"in": 5.0, "out": 25.0, "src": "anthropic first-party (skill claude-api)"},
    "gpt-5.5": {"in": 5.0, "out": 30.0, "src": "developers.openai.com/api/docs/pricing (Standard, <272K) leído 16-ago-2026"},
}


class UsageMeter:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.phase = "init"
        self.rows: list[dict] = []
        self._installed = False
        self.proveedores_instalados: list[str] = []
        self.errores_instalacion: list[str] = []

    def disponible(self) -> bool:
        """(Sol r34) «coste medido» solo si al menos un SDK quedó envuelto; si no, el recibo debe decir
        NO MEDIDO en vez de $0."""
        return bool(self.proveedores_instalados)

    def install(self) -> None:
        if self._installed:
            return
        meter = self
        try:
            import anthropic.resources.messages as am
            orig_a = am.Messages.create

            def a_create(this, *args, **kwargs):
                t0 = time.time()
                resp = orig_a(this, *args, **kwargs)
                u = getattr(resp, "usage", None)
                meter._add("anthropic", kwargs.get("model"),
                           getattr(u, "input_tokens", 0) or 0, getattr(u, "output_tokens", 0) or 0,
                           getattr(u, "cache_read_input_tokens", 0) or 0,
                           getattr(u, "cache_creation_input_tokens", 0) or 0, time.time() - t0)
                return resp
            am.Messages.create = a_create
            self.proveedores_instalados.append("anthropic")
        except Exception as exc:      # SDK ausente: se mide lo que haya, y se DECLARA
            self.errores_instalacion.append(f"anthropic: {type(exc).__name__}")
        try:
            import openai.resources.chat.completions as oc
            orig_o = oc.Completions.create

            def o_create(this, *args, **kwargs):
                t0 = time.time()
                resp = orig_o(this, *args, **kwargs)
                u = getattr(resp, "usage", None)
                meter._add("openai", kwargs.get("model"),
                           getattr(u, "prompt_tokens", 0) or 0, getattr(u, "completion_tokens", 0) or 0,
                           0, 0, time.time() - t0)
                return resp
            oc.Completions.create = o_create
            self.proveedores_instalados.append("openai")
        except Exception as exc:
            self.errores_instalacion.append(f"openai: {type(exc).__name__}")
        self._installed = True

    def _add(self, provider, model, tin, tout, cache_read, cache_write, secs) -> None:
        with self.lock:
            self.rows.append({"provider": provider, "model": model, "phase": self.phase,
                              "in": int(tin), "out": int(tout), "cache_read": int(cache_read),
                              "cache_write": int(cache_write), "secs": round(secs, 2)})

    def snapshot(self) -> int:
        with self.lock:
            return len(self.rows)

    def summary(self, since: int = 0) -> dict:
        with self.lock:
            rows = self.rows[since:]
        agg: dict[str, dict] = {}
        for r in rows:
            key = f"{r['model']}|{r['phase']}"
            a = agg.setdefault(key, {"model": r["model"], "phase": r["phase"], "calls": 0,
                                     "in": 0, "out": 0, "cache_read": 0, "cache_write": 0})
            a["calls"] += 1
            a["in"] += r["in"]
            a["out"] += r["out"]
            a["cache_read"] += r["cache_read"]
            a["cache_write"] += r["cache_write"]
        return {"n_calls": len(rows),
                "by_model_phase": sorted(agg.values(), key=lambda x: (x["model"] or "", x["phase"]))}


def cost_of(summary: dict, prices: dict | None = None) -> dict:
    prices = prices or PRICES_USD_PER_M
    total = 0.0
    assumed = False
    by_model: dict[str, dict] = {}
    for a in summary["by_model_phase"]:
        p = prices.get(a["model"] or "")
        if p is None:
            b = by_model.setdefault(a["model"], {"usd": None, "in": 0, "out": 0, "calls": 0, "price": "DESCONOCIDO"})
            b["in"] += a["in"]; b["out"] += a["out"]; b["calls"] += a["calls"]
            continue
        usd = a["in"] / 1e6 * p["in"] + a["out"] / 1e6 * p["out"]
        b = by_model.setdefault(a["model"], {"usd": 0.0, "in": 0, "out": 0, "calls": 0, "price": p["src"]})
        b["usd"] += usd; b["in"] += a["in"]; b["out"] += a["out"]; b["calls"] += a["calls"]
        total += usd
        if "SUPUESTO" in p["src"]:
            assumed = True
    for b in by_model.values():
        if b["usd"] is not None:
            b["usd"] = round(b["usd"], 4)
    return {"usd_total": round(total, 4), "usd_incluye_precio_supuesto": assumed,
            "usd_incluye_modelo_sin_precio": any(b["usd"] is None for b in by_model.values()),
            "by_model": by_model}


METER = UsageMeter()
