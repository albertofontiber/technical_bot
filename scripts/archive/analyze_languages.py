#!/usr/bin/env python3
"""Análisis de idiomas del corpus — apoyo a la decisión de política de idiomas.

(A) De los docs detectados PT/FR/IT/?: ¿el nombre sugiere multilingüe-con-ES
    (mi heurística de idioma primario falló) o monolingüe real no-ES?
(B) ¿Cuántos manuales son 'el mismo en varios idiomas'? — valida el riesgo de
    chunks repetidos ES/EN.
"""
import sys
import json
import os
import re
import collections

sys.stdout.reconfigure(encoding="utf-8")

rows = json.load(open("logs/corpus_diagnosis.json", encoding="utf-8"))

# Tokens de idioma que aparecen en nombres de manuales PCI
LANG_TOKENS = r"\b(ES|EN|GB|UK|FR|IT|DE|PT|NL|ESP|ENG|FRA|ITA|DEU|POR|SP|spanish|english|french)\b"
ES_HINT = re.compile(r"\b(ES|ESP|SP|spanish|español|espanol|castellano)\b", re.IGNORECASE)
LANG_RE = re.compile(LANG_TOKENS, re.IGNORECASE)


def base_key(name):
    """Nombre normalizado sin tokens de idioma ni extensión — para agrupar
    el mismo manual en varios idiomas."""
    n = os.path.splitext(name)[0]
    n = LANG_RE.sub("", n)
    n = re.sub(r"[_\-\s]+", " ", n).strip().lower()
    return n


# === (A) Análisis de los no-ES ===
no_es = [r for r in rows if r.get("lang") in ("pt", "fr", "it", "?")]
print(f"=== (A) {len(no_es)} docs detectados como PT/FR/IT/? ===\n")

con_es_en_nombre = []
monoling_real = []
for r in no_es:
    name = os.path.basename(r["path"])
    if ES_HINT.search(name):
        con_es_en_nombre.append(r)
    else:
        monoling_real.append(r)

print(f"  Nombre INCLUYE indicador de ES (multilingüe con español, mi detección falló): {len(con_es_en_nombre)}")
print(f"  Nombre SIN indicador de ES (candidato a monolingüe no-ES real):              {len(monoling_real)}")

# desglose de los candidatos monolingües por idioma detectado
by_lang = collections.Counter(r["lang"] for r in monoling_real)
print(f"\n  Desglose de los {len(monoling_real)} candidatos monolingües no-ES:")
for l, n in by_lang.most_common():
    print(f"    {l}: {n}")

print(f"\n  Ejemplos de candidatos monolingües no-ES (primeros 25):")
for r in monoling_real[:25]:
    print(f"    [{r['lang']}] {os.path.basename(r['path'])[:70]}")

# === (B) Manuales que existen en varios idiomas ===
print(f"\n\n=== (B) Manuales con varias versiones de idioma (riesgo chunk repetido) ===\n")
groups = collections.defaultdict(list)
for r in rows:
    name = os.path.basename(r["path"])
    if LANG_RE.search(name):  # solo nombres que llevan token de idioma
        groups[base_key(name)].append((r.get("lang"), name))

multi = {k: v for k, v in groups.items() if len(v) > 1}
print(f"  Grupos de nombre-base con >1 versión: {len(multi)}")
print(f"  Total de archivos implicados: {sum(len(v) for v in multi.values())}")
print(f"\n  Ejemplos (nombre-base → versiones):")
for k, v in list(multi.items())[:12]:
    langs = ", ".join(sorted(set(l for l, _ in v)))
    print(f"    '{k[:50]}' → {len(v)} archivos [{langs}]")
