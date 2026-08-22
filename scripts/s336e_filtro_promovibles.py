#!/usr/bin/env python
"""s336e — los 20 «promovibles» de s336c, pasados por R19/R20/R21 antes de plan.

`PROMOVIBLE` en s336c significa una cosa concreta y limitada: **el canónico está
citado en el PDF y también en `chunks_v2`, y ninguno de sus ids es
`unresolved:`**. Eso es una condición de EVIDENCIA, no una adjudicación. Entre
la evidencia y el plan hay tres filtros que ya me han mordido antes:

  · **R19 (producto-hood)** — que el token esté citado no lo hace producto. Un
    `*.exe` es el ejecutable de un software, no el software (R10 dice que el
    software SÍ es producto: el nombre correcto es el del programa). Una sigla
    de 3 letras o un «Serie N» son familia o ruido, no modelo.
  · **SUJETO vs REFERENCIA CRUZADA** — un manual que nombra un producto en la
    página 32 y no en las 3 primeras probablemente habla de OTRA cosa y lo cita
    de pasada. Es el mecanismo que ya nos costó las 32 atestaciones «sin cita»
    de s334d: deducir que el paraguas lo traía en vez de leerlo.
  · **R21 (colisión pendiente)** — dos formas, y la segunda me la enseñó el gate:
    (a) el mismo canónico existe en DOS MARCAS y la fusión está en la cola de
    Alberto → promover los dos lados por separado PRE-EMPTE su adjudicación;
    (b) el canónico ya es **ALIAS de otro producto consumible** → el candidate es
    un gemelo redundante y lo que toca es un redirect, no una promoción. Mi
    primera versión sólo cruzaba canónico↔canónico y dejó pasar
    `notifier:notifier-inspire-e10`, cuyo nombre ya es alias de
    `notifier:inspire-e10`; el gate lo paró en la validación del catálogo
    («COLISIONA con canonical_model … exact pisaría el alias»). Aquí se
    comprueban las dos, para que no dependa de que el gate lo cace.

Salida: los que sobreviven (con su razón) y los que no (con la regla que los
para). NADA se aplica.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
sys.path.insert(0, str(ROOT))
from src.rag import catalog_store as cs                        # noqa: E402

DIAG = ROOT / "evals/s336c_diagnostico_huerfanos.json"
SALIDA = ROOT / "evals/s336e_filtro_promovibles.json"
#: Si el canónico sólo aparece a partir de esta página, huele a referencia
#: cruzada y no a sujeto. Umbral declarado, no escondido: es una HEURÍSTICA que
#: manda a revisión, nunca una baja automática.
PAGINA_SUJETO = 5


def r19(token: str) -> tuple[bool, str]:
    """¿El token identifica un PRODUCTO? Devuelve (pasa, motivo)."""
    t = (token or "").strip()
    if re.search(r"\.(exe|dll|msi|bat|zip)$", t, re.I):
        return False, ("R19/R10: es el EJECUTABLE, no el software. El producto "
                       "consultable es el programa; el canónico debería ser su nombre")
    if not re.search(r"[A-Za-z]", t):
        return False, "R19: sólo dígitos — el detector los excluye a propósito"
    if re.match(r"^(serie|series|family|familia)\b", t, re.I):
        return False, "R19: es una FAMILIA («Serie N»), no un modelo"
    letras = re.sub(r"[^A-Za-z]", "", t)
    if len(t.split()) == 1 and not re.search(r"\d", t) and len(letras) <= 3:
        return False, (f"R19: sigla de {len(letras)} letras sin dígitos — pasa la cita "
                       "sin identificar nada (mismo mecanismo que `notifier:eia-485`)")
    if re.search(r"[()]", t):
        return False, "R19: el canónico lleva paréntesis — el detector no lo verá tal cual"
    return True, "identificador con forma de modelo"


def main() -> int:
    diag = json.loads(DIAG.read_text("utf-8"))
    cat = cs.load()
    prom = [f for f in diag["filas"] if f["bucket"] == "PROMOVIBLE"]

    def _k(s: object) -> str:
        return re.sub(r"[^a-z0-9]+", "", str(s or "").lower())

    # R21(a): ¿el mismo canónico existe en MÁS DE UNA marca?
    por_canon: dict[str, set[str]] = defaultdict(set)
    for pid, p in cat.products.items():
        por_canon[_k(p.get("canonical_model"))].add(pid.split(":", 1)[0])
    # R21(b): ¿el canónico ya es ALIAS de un producto CONSUMIBLE distinto?
    alias_de: dict[str, set[str]] = defaultdict(set)
    for a in cat.aliases:
        tgt = str(a.get("id", ""))
        if cat._consumable(tgt):
            alias_de[_k(a.get("alias"))].add(tgt)

    pasan, paran = [], []
    for f in prom:
        tok = (f["canonico_citado"] or [""])[0]
        ok, motivo = r19(tok)
        clave = _k(tok)
        marcas = por_canon.get(clave, set())
        pags = f.get("paginas_donde_cita") or []
        # el gemelo se mide contra los ids DE ESTA fila: un alias que apunta al
        # propio candidate no es colisión, es su propio nombre largo
        gemelos = sorted(alias_de.get(clave, set()) - set(f["ids"]))
        if not ok:
            paran.append({**f, "regla": "R19", "motivo": motivo, "token": tok})
        elif gemelos:
            paran.append({**f, "regla": "R21", "token": tok, "gemelos": gemelos,
                          "motivo": (f"«{tok}» ya es ALIAS de {gemelos}, que SÍ es consumible: "
                                     "el candidate es un gemelo redundante. Toca un REDIRECT "
                                     "(adjudicación de Alberto), no una promoción")})
        elif len(marcas) > 1:
            paran.append({**f, "regla": "R21", "token": tok,
                          "motivo": (f"el canónico «{tok}» existe en {sorted(marcas)} — la "
                                     "fusión está en la cola de Alberto; promover los dos "
                                     "lados por separado pre-empta su adjudicación")})
        elif pags and min(pags) > PAGINA_SUJETO:
            paran.append({**f, "regla": "SUJETO", "token": tok,
                          "motivo": (f"el canónico sólo aparece a partir de la página "
                                     f"{min(pags)}: huele a referencia cruzada, no a sujeto "
                                     "— hay que leer el documento antes de atestarlo")})
        else:
            pasan.append({**f, "token": tok, "motivo": motivo,
                          "primera_pagina": min(pags) if pags else None})

    print(f"=== LOS {len(prom)} «PROMOVIBLES», POR R19/R21/SUJETO ===\n")
    print(f"  PASAN ... {len(pasan):2d}")
    for f in pasan:
        print(f"     {f['source_file'][:40]:42s} {f['token'][:22]:24s} "
              f"pág.{f['primera_pagina']}  {f['ids'][:2]}")
    print(f"\n  PARAN ... {len(paran):2d}")
    for r in ("R19", "R21", "SUJETO"):
        g = [x for x in paran if x["regla"] == r]
        if not g:
            continue
        print(f"\n    ── {r} ({len(g)})")
        for f in g:
            print(f"       {f['source_file'][:38]:40s} «{f['token'][:20]}»")
            print(f"          {f['motivo'][:104]}")

    SALIDA.write_text(json.dumps(
        {"que_es": "s336e · los 20 PROMOVIBLES de s336c filtrados por R19 (producto-hood), "
                   "R21 (colisión de marca pendiente de adjudicación) y sujeto-vs-referencia "
                   "cruzada. `PROMOVIBLE` era una condición de EVIDENCIA, no una "
                   "adjudicación. NADA aplicado.",
         "umbral_pagina_sujeto": PAGINA_SUJETO,
         "n_entrada": len(prom), "n_pasan": len(pasan), "n_paran": len(paran),
         "por_regla": dict(Counter(x["regla"] for x in paran)),
         "pasan": pasan, "paran": paran}, ensure_ascii=False, indent=1), "utf-8")
    print(f"\n→ {SALIDA}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
