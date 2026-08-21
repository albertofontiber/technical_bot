#!/usr/bin/env python3
"""s331 — CENSO de la pasada de Alberto sobre el packet v3: ¿en qué acertó la
recomendación y en qué la corrigió?

POR QUÉ EXISTE. Alberto pidió que «aprendiese» de la clasificación. La tentación
es leer sus notas y escribir lecciones que suenen bien; eso es exactamente el
ritual que DEC-072 prohíbe. Antes de escribir una sola regla hay que medir DOS
cosas sobre las anotaciones reales:

  1. **La calibración**: cuántas filas confirmó tal cual. Cada confirmación es
     trabajo suyo que el sistema podría haberle ahorrado — es el numerador del
     caso de la automatización, y no se puede estimar a ojo.
  2. **Las correcciones**: cuáles corrigió y qué clase de fallo revela cada una.
     Sólo esas justifican una regla nueva.

Una regla nacida de una fila que Alberto CONFIRMÓ no es aprendizaje: es ruido
que endurece un acierto y encima parece progreso.

CÓMO CLASIFICA — TRES clases, no dos (corrección del dúo r40, Fable medio).
La primera versión de este script usaba DOS definiciones incompatibles de
«acuerdo» en sus dos mitades: `censar` exigía que la nota fuese SÓLO un
asentimiento y `acierto_de_patrones` sólo que EMPEZARA por uno. Consecuencia:
«OK con juez. este doc va sobre la familia FAAST LT» salía a la vez como
«corrección» y como acierto, y el numerador que justifica escribir reglas nuevas
quedaba inflado **en la dirección que favorecía mi propia propuesta**. Reconciliado
con una sola escala de tres:

  · CONFIRMACIÓN PURA — la nota entera es un asentimiento (`OK`, `OK con juez`).
  · CONFIRMACIÓN CON MATIZ — empieza por asentimiento y añade algo («OK con juez,
    pero ojo que FAAST LT es la familia»). No es un fallo: es donde nace una regla
    SIN que se haya tomado ninguna decisión equivocada.
  · CORRECCIÓN — no empieza por asentimiento. Aquí sí hubo error.

Ante la duda, la clase más severa: un falso «confirmación» inflaría la cifra que
justifica automatizar.

Uso:  python scripts/s331_censo_anotaciones.py <packet_anotado.md>
"""
from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

#: Una nota de Alberto. Él escribe indistintamente `Alberto:` y `alberto:`.
_NOTA = re.compile(r"^\s*alberto:\s*(.*)$", re.IGNORECASE)
#: La cabecera de una fila del packet: `- [ ] \`id\` (canónico)`.
_FILA = re.compile(r"^-\s*\[[ xX]\]\s*`([^`]+)`")
#: El documento del que sale la fila.
_DOC = re.compile(r"^\s*doc\s+`([^`]+)`")

#: Asentimientos puros. Se comparan sobre el texto ya normalizado (sin tildes,
#: sin puntuación final). `ok con juez`, `ok a hssd`, `ok con propuesta del
#: juez`… todos son «adelante con lo propuesto» y NO llevan instrucción.
_ASENTIMIENTO = re.compile(
    r"^(ok|vale|correcto|de acuerdo|adelante|si)"
    r"(\s+(con|a|al|para|con la|con el)\s+"
    r"(el\s+)?(juez|propuesta( del juez)?|juez\.?|hssd|familia\s+\S+|"
    r"lo propuesto|la propuesta))?\.?$"
)


def _normalizar(texto: str) -> str:
    t = texto.strip().lower()
    for a, b in (("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u")):
        t = t.replace(a, b)
    return re.sub(r"\s+", " ", t).strip(" .,;")


def censar(ruta: Path) -> dict:
    lineas = ruta.read_text("utf-8").splitlines()
    fila_actual, doc_actual = "", ""
    confirmaciones, matizadas, correcciones = [], [], []
    for linea in lineas:
        m = _FILA.match(linea)
        if m:
            fila_actual, doc_actual = m.group(1), ""
            continue
        m = _DOC.match(linea)
        if m:
            doc_actual = m.group(1)
            continue
        m = _NOTA.match(linea)
        if not m:
            continue
        texto = m.group(1).strip()
        if not texto or "escribe tu nota" in texto.lower():
            continue          # la línea de instrucciones del encabezado
        registro = {"id": fila_actual, "doc": doc_actual, "texto": texto}
        if _ASENTIMIENTO.match(_normalizar(texto)):
            confirmaciones.append(registro)
        elif _EMPIEZA_OK.match(texto):
            matizadas.append(registro)
        else:
            correcciones.append(registro)
    return {"confirmaciones": confirmaciones, "matizadas": matizadas,
            "correcciones": correcciones}


#: La cabecera de la recomendación que el packet imprimió para una fila.
_RECO = re.compile(r"🎯 \*\*Recomendación afinada\*\*[^\n]*")
#: Un asentimiento AL PRINCIPIO de la nota. Más laxo que `_ASENTIMIENTO` a
#: propósito: aquí sólo se pregunta «¿empezó diciendo que sí?», y un «OK con
#: juez, pero ojo que…» cuenta como acuerdo con lo recomendado.
_EMPIEZA_OK = re.compile(r"^(ok|vale|correcto|de acuerdo)\b", re.IGNORECASE)


def acierto_de_patrones(ruta: Path) -> dict:
    """¿Acertó cada patrón (P1…P5) que el packet recomendaba?

    ES LA CIFRA QUE DECIDE QUÉ SE PUEDE AUTOMATIZAR, y por eso se mide sobre la
    población de ESTE packet y no se hereda del anterior: la recomendación del
    v3 decía «P1: seguir al juez, es el patrón que firmaste 9 veces» — cierto en
    §1.B del v2, y una tasa base ESTALE para las filas del v3. Auto-aplicar un
    patrón con la tasa de otra población es la forma silenciosa de escribir
    decisiones equivocadas en bloque.

    Una recomendación impresa en la cabecera de un grupo se arrastra a las filas
    de ese grupo (así se imprime en el packet).
    """
    texto = ruta.read_text("utf-8")
    por_patron: dict[str, dict] = {}
    for bloque in re.split(r"\n(?=- \[[ xX]\] )", texto):
        cab = _RECO.search(bloque)
        m = _FILA.match(bloque)
        if not m:
            continue
        nota = re.search(r"^\s*alberto:\s*(.+)$", bloque, re.IGNORECASE | re.MULTILINE)
        if not cab or not nota:
            continue
        de_acuerdo = bool(_EMPIEZA_OK.match(nota.group(1).strip()))
        for p in re.findall(r"\[(P\d)\]", cab.group(0)):
            d = por_patron.setdefault(p, {"ok": 0, "no": 0, "filas": []})
            d["ok" if de_acuerdo else "no"] += 1
            d["filas"].append((m.group(1), de_acuerdo, nota.group(1).strip()[:70]))
    return por_patron


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    r = censar(Path(argv[1]))
    conf, mat, corr = r["confirmaciones"], r["matizadas"], r["correcciones"]
    total = len(conf) + len(mat) + len(corr)
    print(f"=== CENSO de {argv[1]} ===")
    print(f"anotaciones: {total}  ·  confirmación pura: {len(conf)}  ·  "
          f"confirmación con matiz: {len(mat)}  ·  corrección: {len(corr)}")

    print("\n--- CONFIRMACIÓN PURA (la recomendación acertó; trabajo evitable) ---")
    for c in conf:
        print(f"  · {c['id']:34s} «{c['texto'][:50]}»")

    print("\n--- CONFIRMACIÓN CON MATIZ (regla nueva SIN decisión equivocada) ---")
    for c in mat:
        print(f"  · {c['id']:34s} «{c['texto'][:70]}»")

    print("\n--- CORRECCIONES (aquí hubo error, y aquí está el aprendizaje) ---")
    for s in corr:
        print(f"\n  · {s['id']}  [{s['doc'][:44]}]")
        print(f"    {s['texto'][:600]}")

    # Un mismo id repetido N veces = N decisiones idénticas pedidas N veces.
    repes = (Counter(s["id"] for s in corr) + Counter(c["id"] for c in mat)
             + Counter(c["id"] for c in conf))
    caros = [(i, n) for i, n in repes.most_common() if n > 1]
    if caros:
        print("\n--- IDS QUE EL PACKET PIDIÓ MÁS DE UNA VEZ ---")
        print("    (misma decisión, repetida: el packet debería agrupar por id)")
        for i, n in caros:
            print(f"  · {i:34s} ×{n}")

    # EL REPARTO QUE IMPORTA. No «cuántas notas escribió» sino «cuántas
    # DECISIONES distintas tomó», y de esas cuántas eran evitables. Es el
    # numerador del caso de la automatización y por eso se calcula, no se
    # estima; confundir una fila repetida con una decisión nueva llevaría a
    # atacar el problema equivocado.
    #
    # CAVEAT que el dúo r40 obligó a poner aquí, no en una nota al pie: el
    # recuento de duplicadas es de ANOTACIONES, y una anotación repetida no
    # implica una decisión repetida — hay 3 ids con decisiones distintas por
    # documento. El número de abajo es el techo del ahorro, no el ahorro.
    distintos = set(repes)
    conf_ids = {c["id"] for c in conf}
    mat_ids = {c["id"] for c in mat}
    corr_ids = {s["id"] for s in corr}
    # Un id con notas de varias clases cuenta por la MÁS SEVERA: la instrucción
    # manda sobre el asentimiento.
    solo_conf = conf_ids - mat_ids - corr_ids
    solo_mat = mat_ids - corr_ids
    duplicadas = total - len(distintos)
    print("\n--- EL REPARTO QUE IMPORTA ---")
    print(f"  anotaciones escritas ............ {total}")
    print(f"  decisiones DISTINTAS ............ {len(distintos)}")
    print(f"  anotaciones duplicadas .......... {duplicadas} "
          f"({duplicadas * 100 // max(1, total)}% del esfuerzo)")
    print("     ⚠ NO todas son eliminables (dúo r40, Sol crítico): «mismo id = "
          "misma decisión» es FALSO.")
    print("     3 ids repetidos llevan decisiones DISTINTAS por documento "
          "(notifier:nfs-32-001, xtralis:vesda,")
    print("     notifier:airsense) y agrupar por id a secas las perdería. La "
          "clave es (id × operación).")
    print(f"  de las distintas, puro «OK» ..... {len(solo_conf)} "
          f"({len(solo_conf) * 100 // max(1, len(distintos))}% — la "
          f"recomendación ya acertaba)")
    print(f"  de las distintas, «OK» + matiz ... {len(solo_mat)} "
          f"← regla nueva SIN decisión equivocada")
    print(f"  de las distintas, CORRECCIÓN .... {len(corr_ids)} "
          f"← aquí hubo error de verdad")

    print("\n--- ACIERTO DE CADA PATRÓN RECOMENDADO ---")
    print("    (el umbral de auto-aplicación sale de AQUÍ, no de la población "
          "anterior)")
    pat = acierto_de_patrones(Path(argv[1]))
    tot_ok = tot = 0
    for p in sorted(pat):
        d = pat[p]
        n = d["ok"] + d["no"]
        tot_ok += d["ok"]
        tot += n
        print(f"\n  {p}: {d['ok']}/{n} ({d['ok'] * 100 // max(1, n)}%)")
        for pid, ok, t in d["filas"]:
            print(f"      {'OK ' if ok else '>>>'} {pid:32s} «{t}»")
    print(f"\n  TOTAL: {tot_ok}/{tot} ({tot_ok * 100 // max(1, tot)}%)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
