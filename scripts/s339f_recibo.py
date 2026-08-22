#!/usr/bin/env python3
"""s339f — el recibo del lote, construido con `aplicar_plan`, no con mi intérprete.

Sol (ronda 2): «huérfanos 82→27, abre 0, validate limpio» seguía saliendo de `s339c`, el
simulador propio cuyo defecto declarado era justamente no representar el lote real.
Reutilizar sus cifras conserva el framing inválido aunque los números coincidan por
casualidad. Este script las recalcula sobre el catálogo que produce **el mismo código que
escribirá** (`s324_lote_firmado_writer.aplicar_plan`), y comprueba además tres cosas que
sólo se ven end-to-end:

  · **huérfanos** antes/después — para lo que sirve el lote.
  · **findability por marca** — que cada `vendido_bajo` de R3 llegue a la fila que
    `_productos_marca` mira de verdad (fila `activo`, no un redirect). Aquí es donde ITAC
    fallaba en silencio.
  · **paraguas** — que los que se emitan expandan; uno inerte es una fila que miente.
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "src"))
sys.path.insert(0, str(RAIZ / "scripts"))

from src.rag import catalog_store as cs                                    # noqa: E402
from scripts.s324_lote_firmado_writer import aplicar_plan                  # noqa: E402

PLAN = RAIZ / "evals" / "s339e_plan.json"
SALIDA = RAIZ / "evals" / "s339f_recibo.json"


def huerfanos(cat: cs.Catalog) -> set[str]:
    out = set()
    for d in cat.doc_map:
        ids = [str(e.get("id", "")) for e in d.get("entries", [])]
        if not any(cat._consumable(i) for i in ids):
            out.add(str(d.get("source_file", "")))
    return out


def alcanzable_como(cat: cs.Catalog, pid: str, marca: str) -> bool:
    """Réplica de `_productos_marca` (src/bot/telegram_bot.py): namespace del id **o**
    `vendido_bajo`, y SÓLO sobre filas `activo` y no-candidate. Si esto da False, la marca
    que Alberto pidió no llega al inventario por mucho que el JSON la lleve escrita."""
    import re
    import unicodedata

    def nk(s: str) -> str:
        p = unicodedata.normalize("NFKD", s or "")
        p = "".join(c for c in p if not unicodedata.combining(c)).lower()
        return re.sub(r"[^a-z0-9]", "", p)

    p = cat.products.get(pid)
    if not p or p.get("estado") != "activo" or p.get("candidate"):
        return False
    return (pid.split(":")[0] == nk(marca)
            or any(nk(v) == nk(marca) for v in p.get("vendido_bajo") or ()))


def main() -> int:
    plan = json.loads(PLAN.read_text("utf-8"))
    with tempfile.TemporaryDirectory() as tmp:
        dst = Path(tmp)
        stats = aplicar_plan(plan, dst, cs.CATALOG_DIR)
        antes, despues = cs.load(), cs.load(dst)
        h0, h1 = huerfanos(antes), huerfanos(despues)
        errores = cs.validate(dst)

        # R3 end-to-end: cada marca pedida, ¿llega?
        marca_ok, marca_ko = [], []
        for vb in plan.get("products_vendido_bajo", []):
            destino = despues.follow_redirect(vb["id"])
            for m in vb["marcas"]:
                fila = {"id": vb["id"], "resuelve_a": destino, "marca": m}
                (marca_ok if alcanzable_como(despues, destino, m) else marca_ko).append(fila)

        # Paraguas: ¿expanden?
        umb_inertes = []
        for u in plan.get("umbrellas_altas", []):
            r = despues.resolve(u["termino"])
            if not r or not r.get("ids"):
                umb_inertes.append({"termino": u["termino"], "resolve": r})

        # ── lo que el dúo pidió antes de firmar ────────────────────────────────────
        # `aplicar_plan` SALTA EN SILENCIO: un redirect cuyo destino no existe, un
        # `vendido_bajo` sobre un id inexistente, una `doc_map_modificacion` cuyo documento
        # no está. Y en ningún punto compara `len(plan[...])` con lo aplicado. Consecuencia:
        # una adjudicación FIRMADA por Alberto puede evaporarse y el recibo decir PASS.
        #
        # Cuadrar contadores no basta: aceptar «faltan 1 de 16 redirects, será un no-op»
        # es aceptar la excusa sin comprobar que aplica. Lo que se verifica aquí es la
        # INTENCIÓN de cada fila del plan contra el estado FINAL — así un salto silencioso
        # sólo es inocuo cuando lo que la fila pedía ya se cumple, y letal en cualquier otro
        # caso, que es exactamente la distinción que faltaba.
        incumplidas = []

        def exige(cond: bool, que: str, fila: dict) -> None:
            if not cond:
                incumplidas.append({"pide": que, "fila": fila})

        for a in plan["products_altas"]:
            pid = a["row"]["id"]
            exige(despues._consumable(pid), f"alta `{pid}` consumible", a["row"])
        for c in plan["products_confirmar"]:
            exige(despues._consumable(c["id"]), f"`{c['id']}` fuera de cuarentena", c)
        for r in plan.get("products_redirect", []):
            exige(despues.follow_redirect(r["id"]) == despues.follow_redirect(r["redirect_to"]),
                  f"`{r['id']}` resuelve a `{r['redirect_to']}`", r)
        for rc in plan.get("products_recanonizar", []):
            prod = despues.products.get(rc["id"]) or {}
            exige(prod.get("canonical_model") == rc["canonical_model"],
                  f"`{rc['id']}` se llama «{rc['canonical_model']}»", rc)
        for q in plan["aliases_quitar"]:
            exige(not any(al.get("alias") == q["alias"] and al.get("id") == q["id"]
                          for al in despues.aliases),
                  f"alias «{q['alias']}» retirado", q)
        for m in plan["doc_map_modificaciones"]:
            fila = next((d for d in despues.doc_map
                         if str(d.get("document_id")) == m["document_id"]), None)
            exige(fila is not None and set(m["entries_nuevas"]) <= {str(e["id"]) for e in fila["entries"]},
                  f"doc_map {m['document_id'][:8]}… lleva {m['entries_nuevas']}", m)

    res = {"intenciones_incumplidas": incumplidas,
           "stats_writer": stats,
           "huerfanos_antes": len(h0), "huerfanos_despues": len(h1),
           "cierra": sorted(h0 - h1), "abre": sorted(h1 - h0),
           "validate_errores": errores,
           "marca_alcanzable": marca_ok, "marca_NO_alcanzable": marca_ko,
           "paraguas_inertes": umb_inertes}
    SALIDA.write_text(json.dumps(res, ensure_ascii=False, indent=1), "utf-8")

    print("stats del writer REAL:", {k: v for k, v in stats.items() if v})
    if incumplidas:
        print(f"\n✗ {len(incumplidas)} INTENCIÓN(ES) DEL PLAN SIN CUMPLIR en el estado final:")
        for i in incumplidas:
            print(f"     {i['pide']}")
    else:
        print("intenciones del plan: TODAS verificadas en el estado final "
              "(no basta con que el writer no fallara)")
    print(f"\nhuérfanos  {len(h0)} → {len(h1)}   (cierra {len(h0 - h1)}, ABRE {len(h1 - h0)})")
    for f in sorted(h1 - h0):
        print(f"   ⚠ nuevo huérfano: {f}")
    print(f"validate: {'limpio' if not errores else str(len(errores)) + ' errores'}")
    for e in errores[:8]:
        print(f"   ✗ {e}")
    print(f"\nR3 (findability por marca): {len(marca_ok)} llegan · {len(marca_ko)} NO llegan")
    for f in marca_ko:
        print(f"   ✗ `{f['id']}` → `{f['resuelve_a']}` no es alcanzable como «{f['marca']}»")
    print(f"paraguas inertes: {len(umb_inertes)}")
    for u in umb_inertes:
        print(f"   ✗ «{u['termino']}» no expande")
    print(f"\n→ {SALIDA.relative_to(RAIZ)}")
    ok = (not errores and not marca_ko and not umb_inertes
          and not (h1 - h0) and not incumplidas)
    print("\nVEREDICTO:", "PASA" if ok else "NO PASA")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
