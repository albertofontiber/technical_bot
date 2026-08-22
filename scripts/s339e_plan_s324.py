#!/usr/bin/env python3
"""s339e — emite el lote en el FORMATO DE PLAN de la puerta `s324`.

Por qué esto y no mi simulador
------------------------------
`s339c` aplicaba las mutaciones con un intérprete propio. El dúo lo partió por ahí: la
simulación no aplicaba `familia`, `alias` ni `marca`, así que «validate limpio» y «abre 0»
describían un subconjunto del lote. Parchear op por op habría dejado el mismo agujero
esperando a la siguiente op nueva.

La raíz es que el efecto lo debe construir **el mismo código que escribirá**, no una copia
mía de lo que creo que hace — que es literalmente la lección que ya está escrita en
`s334_huerfanos_seam1.py`. Emitiendo el plan en el formato de `s324`, `aplicar_plan()`
produce el «después», y con él funcionan sin tocar nada:
  · `s334_huerfanos_seam1.py` — la sonda que ve el estrechamiento hp009/R20 (query-side),
    que el recuento de huérfanos (doc-side) NO puede ver.
  · la propia puerta `s324`, con su freeze, golds, negativos y rollback.

Traducciones que impone el CONTRATO de identidad:
  · «cambiar la marca de un id» no existe: un namespace distinto es un id NUEVO, y el viejo
    queda en `redirect` permanente. Los ids nunca se borran ni se reciclan.
  · «eliminar un id» tampoco: se emite como `redirect`.
"""
from __future__ import annotations

import json
import sys
from importlib import import_module
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "src"))
sys.path.insert(0, str(RAIZ / "scripts"))

from rag import catalog_store as cs  # noqa: E402

PLAN_OPS = RAIZ / "evals" / "s339c_plan_lote.json"
SALIDA = RAIZ / "evals" / "s339e_plan.json"
PROV = "s339 packet REVISION_ALBERTO_HUERFANOS (adjudicación Alberto, 22-ago)"

# Nombres del packet que casan VARIOS documentos a propósito, con la razón. Fuera de esta
# lista, un prefijo ambiguo NO se aplica: casar por `startswith` sobre un nombre truncado y
# escribir en todos los que casen contamina doc_maps ajenos, y con 30+ fabricantes los
# nombres de fichero se solapan cada vez más. Ampliarla es una decisión, no un efecto.
MULTIPLE_ESPERADO = {
    # Filas 16 y 17 de §3: dos copias del MISMO manual («este documento y el de la fila 17
    # son muy similares» — Alberto). El modelo hermano MAD-473 va en las dos.
    "55347200 Manual Sirena Analogica MAD-472 ES ",
}


def retirar_en_cascada(plan: dict, pid: str, entradas: dict[str, set[str]],
                       avisos: list[str]) -> None:
    """Saca `pid` del plan Y todo lo que dependía de él.

    Retirar sólo el alta dejaba el plan malformado en silencio: el `redirect` hacia ese id
    lo salta `aplicar_plan` sin decir nada (su destino ya no está en `ids`), y las entradas
    de `doc_map` que se habían remapeado a él apuntarían a un producto inexistente. Se
    arrastran también `vendido_bajo`, `alias` y las pertenencias a paraguas.
    """
    plan["products_altas"] = [a for a in plan["products_altas"] if a["row"]["id"] != pid]
    plan["products_confirmar"] = [c for c in plan["products_confirmar"] if c["id"] != pid]
    huerfanas = [r for r in plan["products_redirect"] if r["redirect_to"] == pid]
    plan["products_redirect"] = [r for r in plan["products_redirect"] if r["redirect_to"] != pid]
    plan["products_vendido_bajo"] = [v for v in plan["products_vendido_bajo"] if v["id"] != pid]
    plan["aliases_altas"] = [a for a in plan["aliases_altas"] if a["id"] != pid]
    for u in plan["umbrellas_altas"]:
        u["ids"] = [i for i in u["ids"] if i != pid]
    plan["umbrellas_altas"] = [u for u in plan["umbrellas_altas"] if u["ids"]]
    for ids in entradas.values():
        ids.discard(pid)
    avisos.append(f"cascada: retirado `{pid}` y con él {len(huerfanas)} redirect(s) que "
                  f"apuntaban ahí, más sus `vendido_bajo`/alias/paraguas y las entradas de "
                  f"doc_map ya remapeadas — dejarlos habría malformado el plan en silencio")


def main() -> int:
    ops = json.loads(PLAN_OPS.read_text("utf-8"))["operaciones"]
    cat = cs.load()
    por_fichero = {str(d.get("source_file", "")): d for d in cat.doc_map}

    def docs(nombre: str) -> list[dict]:
        """Todos los documentos que casan ese nombre del packet.

        Devuelve LISTA, no uno: el packet trunca los nombres para que quepan en la
        tabla, y las filas 16 y 17 de §3 quedan las dos como «55347200 …MAD-472 ES ».
        Son dos copias del MISMO manual (él lo dice: «este documento y el de la fila 17
        son muy similares»), así que el modelo hermano MAD-473 va en las DOS: elegir una
        dejaría la otra sin la mitad de su sujeto, y descartar por ambigüedad perdía la
        adjudicación entera."""
        if nombre in por_fichero:
            return [por_fichero[nombre]]
        return [v for k, v in por_fichero.items() if k.startswith(nombre)]

    # `retags_db` es obligatorio para `freeze()`. Vacío es la respuesta correcta aquí: este
    # lote no re-etiqueta chunks, sólo toca catálogo.
    plan: dict = {"retags_db": [],
                  "products_altas": [], "products_confirmar": [], "products_retirar": [],
                  "products_recanonizar": [],
                  "products_redirect": [], "products_vendido_bajo": [],
                  "aliases_quitar": [], "aliases_altas": [], "umbrellas_altas": [],
                  "doc_map_modificaciones": [], "doc_map_altas": []}
    nuevos: set[str] = set()
    pendiente_vb: list[int] = []
    entradas: dict[str, set[str]] = {}
    avisos: list[str] = []

    for o in ops:
        op = o["op"]
        if op == "alta":
            plan["products_altas"].append({"row": {
                "id": o["id"], "canonical_model": o["canonical_model"], "estado": "activo",
                "candidate": False, "added_by": "s339",
                "vendido_bajo": o.get("vendido_bajo") or [], "provenance": f"{PROV} · {o['ref']}"}})
            nuevos.add(o["id"])
        elif op == "promover":
            prod = cat.products.get(o["id"]) or {}
            renom = next((x["canonico_nuevo"] for x in ops
                          if x["op"] == "renombrar_canonico" and x["id"] == o["id"]), None)
            plan["products_confirmar"].append({
                "id": o["id"],
                "canonical_model": renom or prod.get("canonical_model", o["id"].split(":")[-1]),
                "provenance_add": f"{PROV} · {o['ref']}: {o['por']}"})
        elif op == "redirect":
            plan["products_redirect"].append({"id": o["id"], "redirect_to": o["redirect_to"],
                                              "motivo": f"{o['ref']} (adjudicación Alberto)"})
        elif op == "eliminar":
            # El contrato prohíbe borrar un id. El merge se expresa como redirect permanente.
            plan["products_redirect"].append({"id": o["id"], "redirect_to": o["reasignar_docs_a"],
                                              "motivo": f"{o['ref']}: merge (los ids no se borran)"})
        elif op == "marca":
            # Cambiar el namespace = id NUEVO + el viejo en redirect. No se reescribe un id.
            viejo = o["id"]
            nuevo = f"{o['marca'].lower().replace(' ', '-')}:{viejo.split(':', 1)[1]}"
            p = cat.products.get(viejo) or {}
            canon = next((x["canonico_nuevo"] for x in ops
                          if x["op"] == "renombrar_canonico" and x["id"] == viejo),
                         p.get("canonical_model", viejo.split(":")[-1]))
            if nuevo not in cat.products and nuevo not in nuevos:
                plan["products_altas"].append({"row": {
                    "id": nuevo, "canonical_model": canon, "estado": "activo",
                    "candidate": False, "added_by": "s339", "vendido_bajo": [o["marca"]],
                    "provenance": f"{PROV} · {o['ref']}: marca adjudicada por Alberto"}})
                nuevos.add(nuevo)
            plan["products_redirect"].append({"id": viejo, "redirect_to": nuevo,
                                              "motivo": f"{o['ref']}: marca adjudicada; el id sin marca reenvía"})
            for m in ops:
                if m["op"] == "doc_map" and m.get("id") == viejo:
                    m["id"] = nuevo
        elif op == "vendido_bajo":
            plan["products_vendido_bajo"].append({"id": o["id"], "marcas": o["marcas"],
                                                  "motivo": f"{o['ref']}: R3 (adjudicación Alberto)"})
            pendiente_vb.append(len(plan["products_vendido_bajo"]) - 1)
        elif op == "alias":
            plan["aliases_altas"].append({"alias": o["alias"], "id": o["id"], "candidate": False,
                                          "added_by": "s339", "tipo": "variante-tipografica",
                                          "provenance": f"{PROV} · {o['ref']}"})
        elif op == "familia":
            term = (cat.products.get(o["paraguas"]) or {}).get("canonical_model") \
                   or o["paraguas"].split(":")[-1].upper()
            u = next((x for x in plan["umbrellas_altas"] if x["termino"] == term), None)
            if u is None:
                u = {"termino": term, "tipo": "familia", "ids": [], "divergent": "unknown",
                     "candidate": False, "added_by": "s339",
                     "provenance": f"{PROV} · {o['ref']}: familia declarada por Alberto"}
                plan["umbrellas_altas"].append(u)
            if o["hijo"] not in u["ids"]:
                u["ids"].append(o["hijo"])
        elif op == "renombrar_canonico":
            # Si viene con `marca`, el alta del id nuevo ya nace con el canónico correcto.
            if not any(m["op"] == "marca" and m["id"] == o["id"] for m in ops):
                plan["products_recanonizar"].append({
                    "id": o["id"], "canonical_model": o["canonico_nuevo"],
                    "motivo": f"{o['ref']} (adjudicación Alberto)"})

    for o in ops:
        if o["op"] != "doc_map":
            continue
        ds = docs(o["manual"])
        if not ds:
            avisos.append(f"{o['ref']}: no encuentro el documento «{o['manual']}» en doc_map")
            continue
        if len(ds) > 1 and o["manual"] not in MULTIPLE_ESPERADO:
            avisos.append(f"{o['ref']}: ✗ «{o['manual']}» casa {len(ds)} documentos y no está "
                          f"declarado como multi-match → `{o['id']}` NO se aplica a ninguno. "
                          f"Casan: {[str(d.get('source_file'))[:60] for d in ds]}")
            continue
        if len(ds) > 1:
            avisos.append(f"{o['ref']}: «{o['manual']}» casa {len(ds)} documentos "
                          f"(multi-match DECLARADO) → `{o['id']}` se añade a los {len(ds)}")
        for d in ds:
            did = str(d["document_id"])
            if did not in entradas:
                entradas[did] = {str(e["id"]) for e in d.get("entries", [])}
            entradas[did].add(o["id"])

    for did, ids in entradas.items():
        plan["doc_map_modificaciones"].append({
            "document_id": did, "entries_nuevas": sorted(ids),
            "regla": "s339", "detalle": "adjudicación de Alberto (packet de huérfanos)"})

    # `vendido_bajo` tiene que aterrizar en la fila que el bot MIRA. Si el id que lo recibe
    # es de los que este mismo lote pasa a `redirect`, la marca se escribe en una fila que
    # `_productos_marca` descarta (filtra `estado == "activo"`) y `aplicar_plan` no sigue
    # redirects para esto. Se reapunta al destino final.
    destino_final = {r["id"]: r["redirect_to"] for r in plan["products_redirect"]}
    for i in pendiente_vb:
        vb = plan["products_vendido_bajo"][i]
        salto = destino_final.get(vb["id"])
        while salto and salto in destino_final:
            salto = destino_final[salto]
        if salto:
            vb["motivo"] += f" (reapuntado desde `{vb['id']}`, que este lote pasa a redirect)"
            vb["id"] = salto
    # Y si el destino es un ALTA de este lote, la marca va directa en la fila nueva: escribirla
    # dos veces no rompe (la op es aditiva) pero el alta es donde se lee primero.
    altas_por_id = {a["row"]["id"]: a["row"] for a in plan["products_altas"]}
    for vb in plan["products_vendido_bajo"]:
        row = altas_por_id.get(vb["id"])
        if row is not None:
            ya = row.get("vendido_bajo") or []
            row["vendido_bajo"] = ya + [m for m in vb["marcas"] if m not in ya]

    # Promover un id que además se REDIRIGE es contradictorio: el redirect resuelve al
    # destino, así que la promoción del origen no aporta nada y su canónico viejo se
    # quedaría contando como consumible en cualquier medida que lea el plan (fue justo lo
    # que hizo aparecer «VISION PLUS» como término de riesgo cuando el lote lo renombra a
    # «VSN Plus»). Se queda sólo el redirect.
    redir_ids = {r["id"] for r in plan["products_redirect"]}
    n0 = len(plan["products_confirmar"])
    plan["products_confirmar"] = [c for c in plan["products_confirmar"] if c["id"] not in redir_ids]
    if n0 != len(plan["products_confirmar"]):
        avisos.append(f"{n0 - len(plan['products_confirmar'])} promoción(es) retiradas por "
                      f"redundantes: el mismo id ya va a `redirect`")

    # Un canónico que pasa a ser CONSUMIBLE entra en `_by_canonical` y se resuelve por
    # exact-match. Si ya existía un alias con la misma normkey, deja de aportar nada y
    # `validate` lo rechaza («exact pisaría el alias»). Lo cazó el writer real al montar
    # el «después» — mi simulador lo había parcheado repuntando alias, que era tapar el
    # síntoma. Se distingue el caso REDUNDANTE del CONFLICTO:
    #   · apunta al mismo producto (siguiendo redirects) → redundante, se retira.
    #   · apunta a OTRO producto → es un homónimo de verdad, y eso lo firma Alberto (R21).
    consumibles: dict[str, str] = {}                     # normkey(canónico) -> id que lo tendrá
    for a in plan["products_altas"]:
        consumibles[cs.norm_token(a["row"]["canonical_model"])] = a["row"]["id"]
    for c in plan["products_confirmar"]:
        prod = cat.products.get(c["id"])
        if prod:
            consumibles[cs.norm_token(prod["canonical_model"])] = c["id"]
    redirigidos = {r["id"]: r["redirect_to"] for r in plan["products_redirect"]}
    for al in cat.aliases:
        nk = cs.norm_token(str(al.get("alias", "")))
        destino_nuevo = consumibles.get(nk)
        if not destino_nuevo:
            continue
        apunta = str(al.get("id", ""))
        efectivo = redirigidos.get(apunta, cat.follow_redirect(apunta))
        if efectivo == destino_nuevo or apunta == destino_nuevo:
            plan["aliases_quitar"].append({"alias": al["alias"], "id": apunta})
        else:
            avisos.append(f"alias «{al['alias']}» apunta a `{apunta}` y chocaría con el canónico "
                          f"de `{destino_nuevo}`: es un homónimo, lo firma Alberto (R21) → "
                          f"la promoción de `{destino_nuevo}` sale del lote")
            retirar_en_cascada(plan, destino_nuevo, entradas, avisos)

    inertes = []
    for u in list(plan["umbrellas_altas"]):
        motivos = []
        exacto = next((pid for pid, pr in cat.products.items()
                       if cs.norm_token(pr.get("canonical_model", "")) == cs.norm_token(u["termino"])
                       and cat._consumable(pid)), None)
        if exacto:
            motivos.append(f"`{exacto}` ya resuelve «{u['termino']}» por exact-match, y `resolve` "
                           f"mira `_by_canonical` ANTES que los paraguas → el paraguas no dispara")
        if u.get("divergent") == "unknown":
            motivos.append("`divergent: \"unknown\"` devuelve cero ids por contrato "
                           "(catalog_store.py:193): no expande")
        if motivos:
            plan["umbrellas_altas"].remove(u)
            inertes.append({"termino": u["termino"], "ids": u["ids"], "motivos": motivos})
            avisos.append(f"paraguas «{u['termino']}» retirado del lote: sería INERTE — "
                          + " · ".join(motivos))

    # `products_altas` duplicadas: `aplicar_plan` las salta en silencio, así que el lote no se
    # rompe, pero «25 altas» contaba filas y no mutaciones. Se deduplican aquí y se declara.
    vistos: dict[str, dict] = {}
    dups = []
    for a in plan["products_altas"]:
        pid = a["row"]["id"]
        if pid in vistos:
            dups.append(pid)
            # conservar la provenance de las dos rutas que lo pidieron
            vistos[pid]["row"]["provenance"] += f" + {a['row']['provenance'].split('·')[-1].strip()}"
            continue
        vistos[pid] = a
    if dups:
        plan["products_altas"] = list(vistos.values())
        avisos.append(f"{len(dups)} alta(s) duplicada(s) fusionadas: {sorted(set(dups))} "
                      f"(dos secciones piden el mismo producto)")

    corpus = [o for o in ops if o["op"].startswith("baja_corpus") or o["op"] == "ingesta_y_superseded"]
    excluidas = [o for o in ops if o["op"] == "EXCLUIDA"]

    plan["_meta"] = {
        "origen": "evals/s339c_plan_lote.json",
        "ops_de_corpus_NO_incluidas": corpus,
        "excluidas": excluidas,
        "avisos": avisos,
        "paraguas_inertes_retirados": inertes,
    }
    SALIDA.write_text(json.dumps(plan, ensure_ascii=False, indent=1), "utf-8")

    for k in ("products_altas", "products_confirmar", "products_redirect",
              "products_vendido_bajo", "aliases_quitar", "aliases_altas", "umbrellas_altas",
              "doc_map_modificaciones"):
        print(f"   {k:<26} {len(plan[k])}")
    print(f"\n   (fuera del plan de catálogo: {len(corpus)} ops de CORPUS, "
          f"{len(excluidas)} secciones EXCLUIDAS)")
    for a in avisos:
        print(f"   ⚠ {a}")
    print(f"→ {SALIDA.relative_to(RAIZ)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
