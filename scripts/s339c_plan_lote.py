#!/usr/bin/env python3
"""s339c — traduce el ledger firmado de Alberto a mutaciones de catálogo, y las SIMULA.

De `evals/s339_ledger_alberto.json` (qué decidió) a una lista explícita de filas a
escribir, aplicada sobre una COPIA del catálogo para medir el efecto real antes de
que nada toque el árbol. G6: el efecto se verifica sobre una copia, no se presume.

Lo que mide, y por qué esas dos cifras y no una:
  · huérfanos que CIERRA  — para lo que sirve el lote.
  · huérfanos que ABRE    — promover puede quitarle a un manual el paraguas que ya
    lo cubría (mecanismo hp009/DEC-091b, R20). Un lote que cierra 40 y abre 5 no
    cierra 40.

No escribe en `data/catalog/`. La escritura es de la puerta `s324`, con su freeze,
sus golds y su rollback.
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
sys.path.insert(0, str(RAIZ))

from rag import catalog_store as cs  # noqa: E402

LEDGER = RAIZ / "evals" / "s339_ledger_alberto.json"
SALIDA = RAIZ / "evals" / "s339c_plan_lote.json"
FICHEROS = ["products.jsonl", "aliases.jsonl", "umbrellas.jsonl", "homonyms.jsonl",
            "relations.jsonl", "doc_map.jsonl", "docrel.jsonl"]
PROV = "s339 packet REVISION_ALBERTO_HUERFANOS (adjudicación Alberto, 22-ago)"

# Grafía CANÓNICA por namespace, tomada de la mayoritaria ya presente en el catálogo.
# Importa: «Morley» y «Morley-IAS» serían dos marcas distintas a efectos de filtro, así
# que un alta con grafía nueva parte la marca en dos silenciosamente.
MARCA = {"detnov": "Detnov", "notifier": "Notifier", "morley": "Morley-IAS",
         "ffe": "Fire Fighting Enterprises", "kac": "KAC", "aritech": "Aritech"}


def _marca(pid: str) -> list[str]:
    ns = pid.split(":", 1)[0]
    if ns not in MARCA:
        raise SystemExit(f"namespace sin grafía canónica declarada: {ns!r} (id {pid}). "
                         f"Añádela a MARCA en vez de dejar que `validate` la rechace.")
    return [MARCA[ns]]


def mutaciones(doc: dict, cat: cs.Catalog) -> list[dict]:
    """Una entrada por cambio atómico. `op` dice qué hace la puerta con ella."""
    ops: list[dict] = []

    def promover(pid: str, ref: str, por: str) -> None:
        p = cat.products.get(pid)
        if p and p.get("candidate"):
            ops.append({"op": "promover", "id": pid, "ref": ref, "por": por})

    def redirect(de: str, a: str, ref: str) -> None:
        ops.append({"op": "redirect", "id": de, "redirect_to": a, "ref": ref})

    for s in doc["secciones"]:
        lec, ref = s.get("lectura"), f"§{s['seccion']}"
        if not lec or lec.get("cambio_de_catalogo") is False:
            continue
        if not lec.get("listo"):
            # Bloqueada = fuera del lote. Sin esto, §2.2 colaba su promoción y volvía a
            # chocar con `desico:tg-1020` — el bloqueo tiene que MORDER, no sólo anotarse.
            ops.append({"op": "EXCLUIDA", "ref": ref, "por": lec.get("bloqueo", "")})
            continue
        tipo = lec["tipo"]

        # El GANADOR de cualquier redirect/fusión tiene que ser consumible, o el
        # redirect no rescata nada (`_consumable` sigue el redirect y ve la cuarentena).
        for campo in ("a", "gana"):
            if lec.get(campo):
                promover(lec[campo], ref, "destino de redirect/fusión")

        if lec.get("de") and lec.get("a") and tipo != "colapso_id":
            redirect(lec["de"], lec["a"], ref)
        if lec.get("redirige") and lec.get("gana"):
            redirect(lec["redirige"], lec["gana"], ref)

        if tipo == "colapso_id":
            # Verificado en s339b: nació y sigue candidate → nada externo lo referenció.
            ops.append({"op": "eliminar", "id": lec["de"], "ref": ref,
                        "por": "candidate desde el alta; su documento pasa a `a`",
                        "reasignar_docs_a": lec["a"]})
            promover(lec["a"], ref, "destino del colapso")

        if lec.get("vendido_bajo"):
            destino = lec.get("a") or lec.get("gana")
            if destino:
                ops.append({"op": "vendido_bajo", "id": destino, "ref": ref,
                            "marcas": lec["vendido_bajo"]})

        if lec.get("familia"):
            hijo = lec.get("id") or lec.get("gana") or lec.get("a")
            if hijo and hijo != lec["familia"]:
                ops.append({"op": "familia", "hijo": hijo, "paraguas": lec["familia"],
                            "ref": ref})

        for pid in lec.get("promover_tambien", []):
            promover(pid, ref, "misma familia, misma marca (adjudicación de Alberto)")

        if tipo == "renombrar_canonico":
            promover(lec["id"], ref, "adjudicado producto por Alberto")
            ops.append({"op": "renombrar_canonico", "id": lec["id"], "ref": ref,
                        "canonico_nuevo": lec["canonico_nuevo"],
                        "quitar_alias": [lec["canonico_nuevo"]]})
            for a in lec.get("alias", []):
                ops.append({"op": "alias", "id": lec["id"], "alias": a, "ref": ref})

        if tipo.startswith("promover") and lec.get("id"):
            pid = lec["id"]
            if pid in cat.products:
                promover(pid, ref, "adjudicado producto por Alberto")
            else:
                ops.append({"op": "alta", "id": pid, "ref": ref,
                            "canonical_model": lec.get("nombre") or pid.split(":")[-1],
                            "vendido_bajo": _marca(pid)})
            for a in lec.get("alias", []):
                ops.append({"op": "alias", "id": pid, "alias": a, "ref": ref})

        for m in lec.get("bajas", []):
            ops.append({"op": "baja_corpus", "manual": m, "ref": ref,
                        "por": "duplicado de idioma (adjudicación de Alberto)"})
        for m in lec.get("bajas_condicionales", []):
            ops.append({"op": "baja_corpus_condicional", "manual": m, "ref": ref,
                        "por": "sólo si 741 y 741I difieren únicamente en idioma"})

        # §7: una adjudicación por fila.
        for pid, f in (lec.get("filas") or {}).items():
            r2 = f"{ref}:{pid.split(':')[-1]}"
            if f.get("accion") == "baja_de_corpus":
                ops.append({"op": "baja_corpus", "id": pid, "ref": r2,
                            "por": "«Elimínalo del corpus»"})
                continue
            if f.get("redirect_a"):
                redirect(pid, f["redirect_a"], r2)
            else:
                promover(pid, r2, "promovido con marca asignada por Alberto")
            if f.get("marca"):
                ops.append({"op": "marca", "id": pid, "marca": f["marca"], "ref": r2})
            if f.get("vendido_bajo"):
                ops.append({"op": "vendido_bajo", "id": pid, "ref": r2,
                            "marcas": f["vendido_bajo"]})
            for m in f.get("modelos", []):
                if m in cat.products:
                    promover(m, r2, "modelo enumerado por Alberto")
                else:
                    ops.append({"op": "alta", "id": m, "ref": r2,
                                "canonical_model": m.split(":")[-1].upper(),
                                "vendido_bajo": _marca(m)})

    # El suelo: cada fila lista deja de ser suelo.
    for f in doc["suelo"]:
        lec = f.get("lectura") or {}
        if not lec.get("listo"):
            continue
        ref = f"suelo:{f['manual'][:28]}"
        if lec.get("accion") == "baja_de_corpus":
            ops.append({"op": "baja_corpus", "manual": f["manual"], "ref": ref,
                        "por": "«retira este manual del corpus»"})
            continue
        pid = lec.get("producto")
        if pid and lec.get("vendido_bajo"):
            ops.append({"op": "vendido_bajo", "id": pid, "ref": ref,
                        "marcas": lec["vendido_bajo"]})
        if pid:
            if pid in cat.products:
                promover(pid, ref, "producto adjudicado por Alberto")
            else:
                ops.append({"op": "alta", "id": pid, "ref": ref,
                            "canonical_model": lec.get("nombre_modelo")
                            or pid.split(":")[-1].upper(),
                            "vendido_bajo": lec.get("vendido_bajo") or _marca(pid)})
            ops.append({"op": "doc_map", "manual": f["manual"], "id": pid, "ref": ref})
            for a in lec.get("alias", []):
                ops.append({"op": "alias", "id": pid, "alias": a, "ref": ref})
    return ops


def simula(ops: list[dict]) -> dict:
    """Aplica lo que es simulable sobre una copia y recuenta huérfanos.

    Sólo se simulan las ops de CATÁLOGO (promover / redirect / alta / doc_map). Las de
    corpus (`baja_corpus`) tocan la BD, no el catálogo, y se cuentan aparte: mezclarlas
    aquí inflaría el cierre con manuales que simplemente desaparecen.
    """
    with tempfile.TemporaryDirectory() as tmp:
        dst = Path(tmp)
        for f in FICHEROS:
            if (cs.CATALOG_DIR / f).exists():
                shutil.copy(cs.CATALOG_DIR / f, dst / f)

        prods = {}
        for l in (dst / "products.jsonl").read_text("utf-8").splitlines():
            if l.strip():
                r = json.loads(l)
                prods[r["id"]] = r

        for o in ops:
            if o["op"] == "promover" and o["id"] in prods:
                prods[o["id"]]["candidate"] = False
            elif o["op"] == "redirect" and o["id"] in prods:
                prods[o["id"]].update(estado="redirect", redirect_to=o["redirect_to"])
            elif o["op"] == "alta":
                prods.setdefault(o["id"], {
                    "id": o["id"], "canonical_model": o["canonical_model"],
                    "estado": "activo", "candidate": False, "added_by": "s339",
                    "vendido_bajo": o.get("vendido_bajo") or _marca(o["id"]),
                    "provenance": PROV})
            elif o["op"] == "renombrar_canonico" and o["id"] in prods:
                prods[o["id"]]["canonical_model"] = o["canonico_nuevo"]
            elif o["op"] == "vendido_bajo" and o["id"] in prods:
                ya = prods[o["id"]].get("vendido_bajo") or []
                prods[o["id"]]["vendido_bajo"] = ya + [m for m in o["marcas"] if m not in ya]
            elif o["op"] == "eliminar":
                prods.pop(o["id"], None)

        (dst / "products.jsonl").write_text(
            "".join(json.dumps(p, ensure_ascii=False) + "\n" for p in prods.values()), "utf-8")

        # doc_map: las altas del suelo enlazan su manual con su producto.
        dm = [json.loads(l) for l in (dst / "doc_map.jsonl").read_text("utf-8").splitlines() if l.strip()]
        por_fichero = {str(d.get("source_file", "")): d for d in dm}

        def busca(n: str):
            if n in por_fichero:
                return por_fichero[n]
            m = [v for k, v in por_fichero.items() if k.startswith(n)]
            return m[0] if len(m) == 1 else None

        for o in ops:
            if o["op"] == "doc_map":
                d = busca(o["manual"])
                if d and not any(e.get("id") == o["id"] for e in d.get("entries", [])):
                    d.setdefault("entries", []).append(
                        {"id": o["id"], "provenance": PROV, "role": "primary", "scope": "doc"})
            elif o["op"] == "eliminar" and o.get("reasignar_docs_a"):
                for d in dm:
                    for e in d.get("entries", []):
                        if e.get("id") == o["id"]:
                            e["id"] = o["reasignar_docs_a"]
        # Un alias que ASCIENDE a canónico no puede seguir siendo alias del mismo id:
        # `validate` lo caza como colisión («exact pisaría el alias»).
        quitar = {(o["id"], a) for o in ops if o["op"] == "renombrar_canonico"
                  for a in o.get("quitar_alias", [])}
        if quitar:
            ruta_a = dst / "aliases.jsonl"
            al = [json.loads(l) for l in ruta_a.read_text("utf-8").splitlines() if l.strip()]
            al = [a for a in al if (a.get("id"), a.get("alias")) not in quitar]
            ruta_a.write_text(
                "".join(json.dumps(a, ensure_ascii=False) + "\n" for a in al), "utf-8")

        # Los ALIAS que apuntaban al id eliminado quedarían colgando (`validate`:
        # «referencia a id inexistente»). Se repuntan al destino del colapso.
        for o in ops:
            if o["op"] == "eliminar" and o.get("reasignar_docs_a"):
                ruta_a = dst / "aliases.jsonl"
                al = [json.loads(l) for l in ruta_a.read_text("utf-8").splitlines() if l.strip()]
                for a in al:
                    if a.get("id") == o["id"]:
                        a["id"] = o["reasignar_docs_a"]
                ruta_a.write_text(
                    "".join(json.dumps(a, ensure_ascii=False) + "\n" for a in al), "utf-8")
        (dst / "doc_map.jsonl").write_text(
            "".join(json.dumps(d, ensure_ascii=False) + "\n" for d in dm), "utf-8")

        antes, despues = cs.load(), cs.load(dst)

        def huerfanos(c: cs.Catalog) -> set[str]:
            out = set()
            for d in c.doc_map:
                ids = [str(e.get("id", "")) for e in d.get("entries", [])]
                if not any(c._consumable(i) for i in ids):
                    out.add(str(d.get("source_file", "")))
            return out

        h0, h1 = huerfanos(antes), huerfanos(despues)
        val = cs.validate(dst)
        return {"antes": len(h0), "despues": len(h1),
                "cierra": sorted(h0 - h1), "abre": sorted(h1 - h0),
                "validate_errores": val}


def main() -> int:
    doc = json.loads(LEDGER.read_text("utf-8"))
    cat = cs.load()
    ops = mutaciones(doc, cat)
    sim = simula(ops)

    por_op: dict[str, int] = {}
    for o in ops:
        por_op[o["op"]] = por_op.get(o["op"], 0) + 1

    res = {"provenance": PROV, "operaciones": ops, "por_tipo": por_op, "simulacion": sim}
    SALIDA.write_text(json.dumps(res, ensure_ascii=False, indent=2), "utf-8")

    print(f"operaciones: {len(ops)}")
    for k, v in sorted(por_op.items(), key=lambda kv: -kv[1]):
        print(f"   {k:<26} {v}")
    print(f"\nhuérfanos  {sim['antes']} → {sim['despues']}   "
          f"(cierra {len(sim['cierra'])}, ABRE {len(sim['abre'])})")
    if sim["abre"]:
        print("  ⚠ nuevos huérfanos:")
        for f in sim["abre"]:
            print(f"      {f}")
    if sim["validate_errores"]:
        print(f"  ✗ validate: {len(sim['validate_errores'])} errores")
        for e in sim["validate_errores"][:12]:
            print(f"      {e}")
    else:
        print("  validate del catálogo simulado: limpio")
    print(f"\n→ {SALIDA.relative_to(RAIZ)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
