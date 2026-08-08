# -*- coding: utf-8 -*-
"""Genera las entradas de sidecar (_metadata.json) para los NUEVOS del lote Casmar.

Convención del sidecar existente: {local_filename, equipo, tipo, idioma, series,
categoria, skus}. Para docs de familia el equipo es la SERIE (precedente «2X-A»);
aquí derivamos el equipo del token de familia del filename cuando el doc aparece
bajo >1 SKU, y el SKU exacto cuando es único. Campo extra `fuente` (procedencia
casmarglobal) — los campos extra son inertes para el consumidor (metadata.py solo
lee equipo/series).

Modo: --aplicar para APPEND real al _metadata.json del canal; sin él, dry (imprime).
"""
import io
import json
import os
import re
import sys

SCRATCH = os.environ.get("S314_WORKDIR", os.getcwd())  # artefactos del harvest (JSONs/staging)
CANAL_DIR = r"C:\Users\Admin\OneDrive - fontiber com\Documents\Claude\Technical Bot\Manuales_Kidde"

_TIPO = {"manual-instalacion": "Manual instalación", "manual-usuario": "Manual usuario",
         "manual-programacion": "Manual programación", "guia-instalacion": "Guía instalación",
         "guia-uso": "Guía uso", "guia-rapida": "Guía rápida", "datasheet": "Datasheet",
         "nota-tecnica": "Nota técnica"}
_CATEG = {"Manual usuario": "Documentación para el usuario", "Guía uso": "Documentación para el usuario",
          "Guía rápida": "Documentación para el usuario"}


def idioma_de(nombre):
    low = nombre.lower()
    if "_ing_" in low or low.endswith(("_ing.pdf", "_en.pdf")) or "_en_" in low:
        return "EN"
    return "ES"


def familia_de(nombre, skus):
    """Serie para docs multi-SKU: prefijo comun de los SKUs (p.ej. NC-PF2/NC-PF4/
    NC-PF4-SC -> NC-PF); SKU exacto si es unico. El token del filename era fragil
    (la x-comodin del portal subia a mayuscula: NC-PFx -> NC-PFX; y sin fecha en
    el nombre caia al stem entero)."""
    if len(skus) == 1:
        return skus[0]
    prefijo = os.path.commonprefix(list(skus)).rstrip("-_ ")
    if len(prefijo) >= 4:
        return prefijo
    # sin prefijo comun util (p.ej. modulo + su KIT): el SKU que aparece EN el
    # filename es el sujeto del doc; el resto son productos que lo contienen.
    plano = os.path.splitext(nombre)[0].upper().replace("_", "-")
    en_nombre = [s for s in skus if s.upper().replace("_", "-").replace(" ", "-") in plano]
    if en_nombre:
        return max(en_nombre, key=len)
    m = re.search(r"(?i)(?:mi|mu|ds|hd|gr|g_inst|g_uso|g_usu|qg)_(?:kidde_)?(.+?)_20\d{4}", nombre)
    token = (m.group(1) if m else os.path.splitext(nombre)[0]).strip("_")
    return token.replace("_", "-").upper()


def main():
    aplicar = "--aplicar" in sys.argv
    report = json.loads(io.open(os.path.join(SCRATCH, "casmar_batch_report.json"), encoding="utf-8").read())
    nuevos = [r for r in report if r["estado"] == "NUEVO"]

    # merge de skus de los duplicados de lote hacia el superviviente
    por_sha = {}
    for r in report:
        if r["estado"] == "NUEVO":
            por_sha[r["sha256"]] = r
    for r in report:
        if r["estado"].startswith("DUP-lote"):
            surv = por_sha.get(r["sha256"])
            if surv:
                surv["skus"] = sorted(set(surv["skus"]) | set(r["skus"]))

    entradas = []
    for r in nuevos:
        tipo = _TIPO[r["tipo"]]
        skus = sorted(set(r["skus"]))
        equipo = familia_de(r["local"], skus)
        entradas.append({
            "local_filename": r["local"],
            "equipo": equipo,
            "tipo": tipo,
            "idioma": idioma_de(r["local"]),
            "series": f"Serie {equipo}" if len(skus) > 1 else "",
            "categoria": _CATEG.get(tipo, "Documentación técnica"),
            "skus": skus,
            "fuente": "casmarglobal.com",
        })

    if not aplicar:
        for e in entradas:
            print(json.dumps(e, ensure_ascii=False))
        print(f"\n{len(entradas)} entradas (dry). --aplicar para append a {CANAL_DIR}\\_metadata.json")
        return

    ruta = os.path.join(CANAL_DIR, "_metadata.json")
    datos = json.loads(io.open(ruta, encoding="utf-8").read())
    existentes = {e.get("local_filename", "").lower() for e in datos}
    anadidas = [e for e in entradas if e["local_filename"].lower() not in existentes]
    datos.extend(anadidas)
    tmp = ruta + ".tmp"
    io.open(tmp, "w", encoding="utf-8").write(json.dumps(datos, ensure_ascii=False, indent=1))
    os.replace(tmp, ruta)
    print(f"APPEND: {len(anadidas)} entradas nuevas ({len(entradas)-len(anadidas)} ya estaban) -> {ruta}")


if __name__ == "__main__":
    main()
