#!/usr/bin/env python3
"""s294_adjudication_packet.py — paquete de ADJUDICACIÓN CIEGA de las capturas (F7).

El dúo de s292 exigió que la adjudicación de «espurio» NO la haga el autor: mi 6/6 de
entonces era optimista y mi tripwire caía sobre el valor observado. Este script no
juzga nada: selecciona una muestra DETERMINISTA y estratificada por forma, la
desordena de manera reproducible (hash del span, sin `random`), y la emite SIN pistas
— ni cuál es la diana de `hp003#4`, ni qué forma capturó cada fila, ni mi opinión.

La taxonomía de espurio y la regla de daño van en el propio paquete, fijadas ANTES.

Uso:  python scripts/s294_adjudication_packet.py [n_muestra]
Salida: evals/s294_adjudication_packet_v1.md  (para el cross-model / Alberto)
"""
from __future__ import annotations

import hashlib
import json
import os
import sys

N = int(sys.argv[1]) if len(sys.argv) > 1 else 60
CENSUS = os.path.join("evals", os.getenv("S294_CENSUS", "s294_siempre_census_v2.json"))
SUFFIX = os.getenv("S294_ROUND", "_r2")


def stable_key(row: dict) -> str:
    return hashlib.sha256(
        (row["span"] + "|" + str(row["chunk_id"])).encode("utf-8")
    ).hexdigest()


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    census = json.load(open(CENSUS, encoding="utf-8"))
    rows = census["capturas"]

    # Estratificación proporcional por forma, selección determinista por hash.
    by_form: dict[str, list[dict]] = {}
    for row in rows:
        by_form.setdefault(row["form"], []).append(row)
    sample: list[dict] = []
    for form, group in sorted(by_form.items()):
        group = sorted(group, key=stable_key)
        quota = max(1, round(N * len(group) / len(rows)))
        sample.extend(group[:quota])
    # La DIANA del lever (hp003#4) entra SIEMPRE en la muestra, sin marca alguna: si
    # su legitimidad no se somete al juicio ciego, el gate no prueba lo que importa.
    diana = next(
        (r for r in rows
         if "desconecte siempre" in r["span"].lower() and "magneto" in r["span"].lower()),
        None,
    )
    if diana is not None and not any(r["span"] == diana["span"] for r in sample):
        sample.append(diana)
    # desorden reproducible: se pierde la agrupación por forma en la vista del juez
    sample = sorted(sample, key=stable_key)

    lines = [
        "# s294 — ADJUDICACIÓN CIEGA de capturas del gatillo «siempre» (L3 v2)",
        "",
        "Eres el ADJUDICADOR. Cada fila es una oración extraída VERBATIM de un manual "
        "técnico de PCI del corpus. El sistema plantea usarlas como **avisos "
        "obligatorios** que se anexarían, citados y verbatim, al final de una respuesta "
        "técnica cuando el fragmento que las contiene se haya servido y la respuesta no "
        "las cubra.",
        "",
        "**Tu tarea, fila por fila:** decidir si la oración es una **OBLIGACIÓN "
        "OPERATIVA REAL** que un técnico debe cumplir (`legitima`), o es **ESPURIA**. "
        "No sabes cuál es la fila que motivó el diseño, ni qué forma sintáctica capturó "
        "cada una: es deliberado.",
        "",
        "## Taxonomía de ESPURIO (pre-registrada, fijada antes de mirar filas)",
        "",
    ]
    for key, desc in census["taxonomia_espurio_PRE_REGISTRADA"].items():
        lines.append(f"- **`{key}`** — {desc}")
    lines += [
        "",
        f"**Regla de daño declarada:** {census['regla_de_dano']}",
        "",
        "## Formato de respuesta (una línea por fila, sin prosa adicional)",
        "",
        "`<n> | legitima|espuria | <clase de la taxonomía o '-'> | <≤12 palabras de motivo>`",
        "",
        "Si una fila te parece dudosa, márcala `espuria` con la clase más cercana: el "
        "coste de un aviso de seguridad espurio es mayor que el de perder uno.",
        "",
        "---",
        "",
        f"## Filas ({len(sample)})",
        "",
    ]
    for index, row in enumerate(sample, start=1):
        lines.append(
            f"**{index}.** «{row['span']}»  \n"
            f"   <sub>fuente: {row['source_file']} · p.{row['page_number']}</sub>"
        )
        lines.append("")

    path = os.path.join(os.getcwd(), "evals", f"s294_adjudication_packet{SUFFIX}.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))

    key_path = os.path.join(os.getcwd(), "evals", f"s294_adjudication_key{SUFFIX}.json")
    with open(key_path, "w", encoding="utf-8") as fh:
        json.dump(
            {
                "probe": "s294_adjudication_key_v1",
                "n_sample": len(sample),
                "n_poblacion_capturas": len(rows),
                "orden": [
                    {
                        "n": i,
                        "chunk_id": r["chunk_id"],
                        "form": r["form"],
                        "lang": r["lang_detectado"],
                        "span_defects": r["span_defects"],
                        "span": r["span"],
                    }
                    for i, r in enumerate(sample, start=1)
                ],
            },
            fh, ensure_ascii=False, indent=1,
        )
    print(f"paquete: {path}\nclave (NO se envía al adjudicador): {key_path}")
    print(json.dumps({"n_muestra": len(sample), "por_forma_en_muestra":
                      {f: sum(1 for r in sample if r["form"] == f) for f in by_form}},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
