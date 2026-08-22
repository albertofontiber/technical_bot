#!/usr/bin/env python3
"""s339b — verifica el ledger de adjudicaciones contra el catálogo VIVO.

El ledger (`s339`) dice lo que Alberto decidió y lo que yo entendí. Este script
pregunta lo único que ninguno de los dos sabe sin mirar: **¿es aplicable?**

Protocolo 1 aplicado a mi propia lectura: antes de llevar nada a la puerta s324,
cada acción se contrasta con el estado real —¿existe el id destino? ¿es consumible?
¿el manual sigue enlazado? ¿el canónico es siquiera detectable?—. Una lectura mía
que no sobrevive a esto NO va al lote: vuelve a Alberto o se rehace.

No escribe en el catálogo. Sólo diagnostica.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
sys.path.insert(0, str(RAIZ))

from rag import catalog_store  # noqa: E402

LEDGER = RAIZ / "evals" / "s339_ledger_alberto.json"
SALIDA = RAIZ / "evals" / "s339b_verificacion.json"


def detectable(canonico: str) -> tuple[bool, str]:
    """¿El detector puede alcanzar este canónico?

    Réplica de las exclusiones reales de `catalog_resolver._add`, que es donde se
    decide de verdad. Crear un producto cuyo canónico el detector no ve es crear
    una fila que no resuelve nada — el fallo de `MADT190_10` (racks `020-59x`).
    """
    t = catalog_store.norm_token(canonico)
    if not t:
        return False, "canónico vacío tras normalizar"
    if not re.search(r"[a-z]", t):
        return False, "sólo dígitos — el detector los excluye a propósito"
    return True, ""


def main() -> int:
    cat = catalog_store.load()
    doc = json.loads(LEDGER.read_text("utf-8"))

    # ¿Qué manuales siguen sin producto consumible? (definición de huérfano)
    docs_por_fichero: dict[str, list[str]] = {}
    for d in cat.doc_map:
        docs_por_fichero.setdefault(str(d.get("source_file", "")), []).extend(
            str(e.get("id", "")) for e in d.get("entries", []))

    def busca(nombre: str) -> str | None:
        """El packet TRUNCA los nombres para que quepan en la tabla («…MAD-450 E»),
        así que comparar por igualdad daba falsos «ya no está en doc_map». Se resuelve
        por prefijo, y sólo si el prefijo es INEQUÍVOCO: dos manuales que comparten
        prefijo truncado (las filas 16/17 de §3) no se pueden desambiguar así."""
        if nombre in docs_por_fichero:
            return nombre
        m = [f for f in docs_por_fichero if f.startswith(nombre)]
        return m[0] if len(m) == 1 else None
    huerfanos = {f for f, ids in docs_por_fichero.items()
                 if not any(cat._consumable(i) for i in ids)}

    hallazgos: list[dict] = []

    def check(ref: str, ok: bool, msg: str, grave: bool = True) -> None:
        if not ok:
            hallazgos.append({"ref": ref, "nivel": "BLOQUEA" if grave else "aviso",
                              "problema": msg})

    def existe(pid: str) -> bool:
        return pid in cat.products

    for s in doc["secciones"]:
        lec, ref = s.get("lectura"), f"§{s['seccion']}"
        if not lec:
            continue
        tipo = lec["tipo"]

        for campo in ("de", "redirige"):
            if lec.get(campo):
                check(ref, existe(lec[campo]), f"el ORIGEN `{lec[campo]}` no existe en products")

        for campo in ("a", "gana", "id", "familia"):
            if lec.get(campo):
                pid = lec[campo]
                if not existe(pid):
                    # Para `promover`/`id` el destino puede ser un id NUEVO: no es fallo.
                    check(ref, tipo.startswith("promover") or campo == "id",
                          f"el DESTINO `{pid}` no existe en products")
                elif campo in ("a", "gana"):
                    if not cat._consumable(pid):
                        # No es un fallo de Alberto: es que el ganador está en cuarentena
                        # y la acción necesita un paso más. Se declara como requisito.
                        hallazgos.append({
                            "ref": ref, "nivel": "REQUISITO",
                            "problema": f"`{pid}` está en cuarentena (candidate) → la acción "
                                        f"necesita PROMOVERLO además de redirigir el otro id; "
                                        f"redirigir hacia un candidate no rescata nada"})

        if tipo == "homonimo":
            for pid in lec.get("ids", []):
                check(ref, existe(pid), f"`{pid}` no existe en products")
            ya = [h for h in cat.homonyms
                  if set(lec.get("ids", [])) & set(h.get("ids", []))]
            check(ref, not ya, f"ya hay un homónimo que cubre estos ids: "
                               f"{[h.get('termino') for h in ya]}", grave=False)

        if tipo == "colapso_id":
            pid = lec["de"]
            p = cat.products.get(pid, {})
            fue_consumible = bool(p) and not p.get("candidate") and p.get("estado") == "activo"
            hallazgos.append({
                "ref": ref, "nivel": "ADJUDICADO" if not fue_consumible else "BLOQUEA",
                "problema": f"`{pid}`: candidate={p.get('candidate')} estado={p.get('estado')!r}. "
                            + ("Nació y sigue en cuarentena → nada externo lo referenció, "
                               "borrarlo NO rompe la inmutabilidad (que protege ids publicados)."
                               if not fue_consumible else
                               "FUE consumible → borrarlo SÍ rompe el contrato de inmutabilidad; "
                               "hay que redirigir y explicárselo a Alberto.")})

        for pid in lec.get("modelos_nuevos", []) + lec.get("modelos", []):
            if existe(pid):
                check(ref, False, f"`{pid}` ya existe (candidate={cat.products[pid].get('candidate')}) "
                                  f"— no es un modelo nuevo", grave=False)

        # §7: cada fila lleva su propia adjudicación.
        for pid, f in (lec.get("filas") or {}).items():
            r2 = f"{ref}:{pid}"
            check(r2, existe(pid), f"`{pid}` no existe en products")
            if f.get("accion") == "baja_de_corpus":
                continue
            if f.get("marca") and existe(pid):
                nuevo = f"{f['marca']}:{pid.split(':', 1)[1]}"
                if existe(nuevo) and nuevo != pid:
                    check(r2, cat._consumable(nuevo),
                          f"`{nuevo}` ya existe pero NO es consumible", grave=False)

        # Los manuales que la sección dice desbloquear, ¿siguen huérfanos?
        reales = {m: busca(m) for m in s["manuales"]}
        perdidos = [m for m, r in reales.items() if r is None]
        ya_ok = [m for m, r in reales.items() if r is not None and r not in huerfanos]
        if perdidos:
            check(ref, False, f"{len(perdidos)} manual(es) del packet ya no están en doc_map: "
                              f"{perdidos[:3]}", grave=False)
        if ya_ok:
            check(ref, False, f"{len(ya_ok)} manual(es) YA tienen producto consumible "
                              f"(otra sesión los resolvió): {ya_ok[:3]}", grave=False)

    # El suelo.
    for f in doc["suelo"]:
        lec, ref = f.get("lectura"), f"suelo:{f['manual'][:32]}"
        if not lec:
            continue
        if busca(f["manual"]) is None:
            check(ref, False, "el manual no está en doc_map", grave=False)
        for campo in ("producto", "familia"):
            if lec.get(campo) and existe(lec[campo]):
                check(ref, cat._consumable(lec[campo]),
                      f"`{lec[campo]}` existe pero NO es consumible", grave=False)
        # ¿Los canónicos que propone son alcanzables por el detector?
        for m in lec.get("modelos", []) or ([lec["producto"].split(":", 1)[-1]]
                                            if lec.get("producto") else []):
            ok, por = detectable(m)
            if not ok:
                check(ref, False, f"canónico «{m}»: {por}")

    res = {
        "huerfanos_hoy": len(huerfanos),
        "hallazgos": hallazgos,
        "bloqueantes": sum(1 for h in hallazgos if h["nivel"] == "BLOQUEA"),
    }
    SALIDA.write_text(json.dumps(res, ensure_ascii=False, indent=2), "utf-8")

    print(f"huérfanos hoy en el catálogo vivo : {len(huerfanos)}")
    print(f"hallazgos                         : {len(hallazgos)} "
          f"({res['bloqueantes']} bloqueantes)\n")
    for h in hallazgos:
        marca = {"BLOQUEA": "✗", "aviso": "·", "ADJUDICADO": "→", "REQUISITO": "+"}[h["nivel"]]
        print(f" {marca} {h['ref']:<30} {h['problema']}")
    print(f"\n→ {SALIDA.relative_to(RAIZ)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
