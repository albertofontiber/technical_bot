"""s303 — cruza el catálogo de los portales Notifier/Morley contra el corpus (chunks_v2).

Entradas
  data/catalog_portales/s303_portales_notifier_morley_v1.json   (844 entradas cosechadas)
  data/catalog_portales/s303_resolved_filenames_v1.json         (url -> nombre de fichero real)
  data/catalog_portales/s303_corpus_source_files.json           (source_file distintos de chunks_v2)

Salidas
  evals/s303_cruce_portales_corpus_v1.json
  evals/s303_cruce_portales_corpus_v1.md

Criterio de cruce — 4 niveles, declarados (de más a menos seguro):
  T1 EXACT       nombre sin extensión, insensible a mayúsculas
  T2 NORM        minúsculas + sin acentos + SOLO alfanuméricos (quita '-', '_', ' ', '.')
  T3 REVLOOSE    T2 tras podar sufijos de revisión FINALES: rvNN / revNN / revX / vNN /
                 issue N / _X (letra suelta) / _copia|_lr|_prelim…
  T4 REVAGNOSTIC quita CUALQUIER token de revisión/fecha (rev 5, 09-07-2026, RevB,
                 20July2015, año suelto) -> detecta «mismo doc, otra edición»
  NO se poda `_NN` final (sub-número de documento en HLSI, no revisión) ni los sufijos de
  IDIOMA (_ES/_EN/_SP/_PT): la versión española y la inglesa son documentos DISTINTOS.
Un fichero del portal que no case en ninguno de los 4 niveles = candidato de adquisición.
Para cada candidato se busca además el vecino más parecido del corpus (difflib >= 0.85)
como aviso explícito de posible falso negativo del cruce.
"""
from __future__ import annotations

import difflib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAT = ROOT / "data" / "catalog_portales" / "s303_portales_notifier_morley_v1.json"
RES = ROOT / "data" / "catalog_portales" / "s303_resolved_filenames_v1.json"
CORP = ROOT / "data" / "catalog_portales" / "s303_corpus_source_files.json"
OUT_JSON = ROOT / "evals" / "s303_cruce_portales_corpus_v1.json"
OUT_MD = ROOT / "evals" / "s303_cruce_portales_corpus_v1.md"

EXT_RE = re.compile(r"\.(pdf|zip|doc|docx|rar|exe|xls|xlsx)$", re.I)
REV_PATTERNS = [
    r"[\s_\-]*(?:rv|rev|revision|version|ver|issue|iss)[\s_\-\.]*\d+[a-z]?$",
    r"[\s_\-]*(?:rv|rev|revision|issue|iss)[\s_\-\.]*[a-z]$",
    r"[\s_\-]*v\d{1,3}$",
    r"[\s_\-]+(?:copia|copy|lr|hr|prelim|preliminar|final|draft|new|old|bis)$",
    r"[_\-][a-z]$",
    # ¡OJO! NO se poda `_NN` final: en la nomenclatura HLSI es un SUB-NÚMERO de documento,
    # no una revisión. Verificado en el corpus: MADT190_01..MADT190_15 son 13 documentos
    # DISTINTOS (product_model ID²NET / ID3000 / LIB3000 / ID-CRA / PSU7A…). Podarlo
    # fabricaba un match falso (MADT190P_02 -> MADT190P_01_C) y habría ocultado
    # candidatos reales de adquisición.
]

# --- tokens de revisión/fecha (T4): mismo documento, edición distinta
# OJO: no se usa `\b` — el guion bajo ES carácter de palabra para el motor regex, así que
# `\brv05\b` NO casa dentro de 'HLSI-MN-025_rv05 NFS Supra'. Se usan lookarounds propios
# que tratan '_' (y cualquier no-alfanumérico) como separador.
NB_L, NB_R = r"(?<![a-z0-9])", r"(?![a-z0-9])"
REVDATE_TOKENS = [
    NB_L + r"\d{1,2}[\-/_\.]\d{1,2}[\-/_\.]\d{2,4}" + NB_R,  # 09-07-2025
    NB_L + r"\d{1,2}[\-/_\.]\d{4}" + NB_R,  # 04-2025
    NB_L + r"\d{1,2}[a-z]{3,9}\d{4}" + NB_R,  # 20july2015
    NB_L + r"(?:rev|revision|rv|issue|iss|edicion)[\s_\-\.]*\d{1,3}[a-z]?" + NB_R,
    NB_L + r"(?:rev|revision|rv|issue|iss)[\s_\-\.]*[a-z]" + NB_R,
    NB_L + r"(?:lr|hr|copia|copy|prelim|preliminar|draft)" + NB_R,
    NB_L + r"(?:19|20)\d{2}" + NB_R,  # año suelto
]
REVDATE_RE = re.compile("|".join(REVDATE_TOKENS))


def fix_mojibake(s: str) -> str:
    """Repara el mojibake de `Content-Disposition`.

    Las cabeceras HTTP se decodifican como latin-1 (RFC 9110), pero el portal envía el
    nombre de fichero en UTF-8: 'programación' (NFD) llega como 'programacioÌ\\x81n'.
    Si el round-trip latin-1 -> utf-8 es válido, ese es el nombre real.
    """
    if not s or all(ord(c) < 128 for c in s):
        return s
    try:
        cand = s.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return s
    return cand


def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def base_name(s: str) -> str:
    # NFC: el portal sirve algunos nombres en forma DESCOMPUESTA (p.ej. "programacio" + U+0301);
    # sin esto, T1 fallaría contra el corpus por una diferencia invisible.
    return unicodedata.normalize("NFC", EXT_RE.sub("", fix_mojibake(s or "").strip()).strip())


def norm(s: str) -> str:
    """T2: minúsculas, sin acentos, solo alfanuméricos."""
    return re.sub(r"[^a-z0-9]+", "", strip_accents(base_name(s).lower()))


def norm_loose(s: str) -> str:
    """T3: T2 tras podar sufijos de revisión finales (iterativo, máx 3 podas)."""
    x = strip_accents(base_name(s).lower())
    for _ in range(3):
        before = x
        for p in REV_PATTERNS:
            x2 = re.sub(p, "", x)
            if x2 != x and len(x2) >= 4:
                x = x2
                break
        if x == before:
            break
    return re.sub(r"[^a-z0-9]+", "", x)


def norm_revagnostic(s: str) -> str:
    """T4: quita CUALQUIER token de revisión/fecha (no solo el final) y luego alfanumérico.

    Sirve para detectar «el mismo documento en otra edición»: p.ej.
      portal  'AM-8100 manual de usuario y programación rev 5 09-07-2025'
      corpus  'AM-8100 manual de usuario y programacion rev 4 30-10-2024'
    Devuelve '' si al podar queda menos de 6 caracteres (clave demasiado débil).
    """
    x = strip_accents(base_name(s).lower())
    x = REVDATE_RE.sub(" ", x)
    x = re.sub(r"[^a-z0-9]+", "", x)
    return x if len(x) >= 6 else ""


# ------------------------------------------------- detección del gemelo español en el corpus
# Marcadores de idioma extranjero que aparecen en los nombres de HLSI. Se EXCLUYEN 'de' y
# 'en' a propósito: son palabras castellanas frecuentes en los propios títulos/ficheros
# ('manual de instalacao') y sustituirlas corrompería la clave.
FOREIGN_MARK = re.compile(
    r"(?<![a-z0-9])(ptbr|pt|portugues|portuguese|francais|french|fr|italiano|ita|it|english|eng|ing)(?![a-z0-9])"
)
ES_MARKS = ["es", "esp", "espanol", "spanish", "sp", "castellano"]


def spanish_variants(fname: str) -> list[str]:
    """Variantes plausibles del MISMO documento en español.

    Dos mecanismos observados en la nomenclatura HLSI:
      1. sufijo 'P' pegado al número de documento -> versión portuguesa
         (MNDT250P/MNDT250, MADT190P_02/MADT190_02, MIE-MI-130P/MIE-MI-130)
      2. marcador de idioma en el nombre (`_PT`, `-PT`, `_Portuguese`, ` IT`, `_ENG`…)
    """
    base = strip_accents(base_name(fname).lower())
    out = []
    # 1) 'P' de portugués pegado a un número de documento
    v = re.sub(r"(?<=\d)p(?![a-z0-9])", "", base)
    if v != base:
        out.append(v)
    # 2) swap de marcador de idioma
    for src in {base, *out}:
        if FOREIGN_MARK.search(src):
            for es in ES_MARKS:
                out.append(FOREIGN_MARK.sub(es, src))
    # 3) código de idioma DENTRO del part-number HLSI de la gama 997-xxx:
    #    '-007-' = portugués, '-005-' = español. Verificado con dos pares del corpus:
    #    997-670-007-3_Operating_PT / 997-670-005-3_Operating_ES  y
    #    997-671-007-3_Configuration_PT / 997-671-005-3_Configuration_ES
    for src in list({base, *out}):
        if re.search(r"\b997-\d{3}-007-", src):
            out.append(re.sub(r"(\b997-\d{3}-)007-", r"\g<1>005-", src))
    return out


# Cualquier marcador de idioma (incluido el español): sirve para preguntar
# «¿tenemos ESTE MISMO documento en ALGÚN idioma?».
ANY_LANG_MARK = re.compile(
    r"(?<![a-z0-9])(espanol|spanish|castellano|esp|es|sp|portuguese|portugues|ptbr|pt|"
    r"english|ingles|eng|ing|en|francais|french|fr|italiano|ita|it|german|aleman|deu|de|"
    r"multilingue|multiling|multi|mlt|lng|nl|br|ar|xp)(?![a-z0-9])"
)


def lang_agnostic_key(fname: str) -> str:
    """Clave con TODOS los marcadores de idioma eliminados.

    Detecta «el mismo documento, otra edición idiomática»: 'Manual SIMEI-HLSI_FR-PT' y
    'Manual SIMEI-HLSI_SP-EN' colapsan a 'manualsimeihlsi'. Devuelve '' por debajo de
    10 caracteres (claves cortas colisionan con demasiada facilidad).
    """
    x = strip_accents(base_name(fname).lower())
    x = REVDATE_RE.sub(" ", x)
    x = ANY_LANG_MARK.sub(" ", x)
    x = re.sub(r"[^a-z0-9]+", "", x)
    return x if len(x) >= 10 else ""


# ---------------------------------------------------------------- clasificación de valor
# Nivel 1 — el documento que más paga: cómo se programa/configura/pone en marcha el equipo.
PROG_KW = [
    "programacion",
    "programacao",
    "programming",
    "configuracion",
    "configuracao",
    "configuration",
    "puesta en marcha",
    "puesta en servicio",
    "commissioning",
    "licencia",
    "licenciamento",
    "licenc",
    "software",
    "firmware",
    "menu",
    "manual tecnico",
    "technical manual",
    "manual de servicio",
]
# Nivel 2 — instalación, uso, mantenimiento, conexionado, guías rápidas (todos los idiomas
# del portal: es / pt / fr / it / de / en).
INSTAL_KW = [
    "instalacion",
    "instalacao",
    "installation",
    "installazione",
    "instrucciones",
    "instruccion",
    "instrucoes",
    "instructions",
    "istruzioni",
    "anleitung",
    "manual de usuario",
    "manual de utilizador",
    "manual de funcionamento",
    "manual de funcionamiento",
    "user manual",
    "manuel",
    "manuale",
    "benutzerhandbuch",
    "handbuch",
    "utilisation",
    "operating",
    "operacion",
    "operacional",
    "mantenimiento",
    "manutencao",
    "maintenance",
    "guia rapida",
    "guia rapido",
    "guide rapide",
    "guida rapida",
    "quick",
    "conexionado",
    "conexion",
    "ligacoes",
    "cableado",
    "wiring",
    "montaje",
    "mounting",
    "anexo",
    "ciberseguridad",
    "ciberseguranca",
    "cybersecurity",
    "manual",
]
DATASHEET_KW = [
    "hoja de caracteristicas",
    "hoja tecnica",
    "ficha tecnica",
    "datasheet",
    "data sheet",
    "caracteristicas tecnicas",
    "declaracion de prestaciones",
    "declaration of performance",
    "certificado",
    "certificate",
    "catalogo",
    "tarifa",
    "folleto",
    "brochure",
]
FAQ_KW = ["como ", "no puedo", "averia", "faq", "solucion", "por que", "que hacer"]


def doc_class(title: str, fname: str) -> str:
    t = strip_accents((title or "").lower())
    f = strip_accents((fname or "").lower())
    blob = t + " " + f
    if any(k in blob for k in DATASHEET_KW):
        return "datasheet/certificado"
    if any(blob.startswith(k) or (" " + k) in blob for k in FAQ_KW):
        return "faq/soporte"
    if any(k in blob for k in PROG_KW):
        return "manual prog/config/puesta-en-marcha"
    if any(k in blob for k in INSTAL_KW):
        return "manual instalacion/uso/conexionado"
    return "otro/indeterminado"


LANG_RE = re.compile(
    r"\b(espanol|english|ingles|frances|aleman|italiano|portugues|multilingue|multilingue)\b"
)


def lang_of(meta: str) -> str:
    m = LANG_RE.search(strip_accents((meta or "").lower()))
    if not m:
        return "sin declarar"
    return {
        "espanol": "es",
        "english": "en",
        "ingles": "en",
        "multilingue": "multi (incl. es)",
        "portugues": "pt",
        "frances": "fr",
        "aleman": "de",
        "italiano": "it",
    }.get(m.group(1), m.group(1))


def family_of(meta: str) -> str:
    m = strip_accents((meta or "")).strip()
    m = re.sub(r"^(Espa[nñ]ol|English|Ingl[eé]s|Franc[eé]s|Alem[aá]n|Italiano|Portugu[eé]s)\s*", "", m, flags=re.I)
    m = re.sub(r"\s*Descargar\s*$", "", m, flags=re.I).strip()
    return m or "(sin familia)"


MODEL_RE = re.compile(r"\b([A-Z][A-Z0-9]{1,}(?:[\-/][A-Z0-9]+)*)\b")
# Números internos de documento de HLSI (MNDT1102, MIDT192, TIDT089…): NO son códigos de
# producto, contaminan la señal de "familia". Se excluyen.
DOCNUM_RE = re.compile(r"^(?:[A-Z]{1,3}DT\d+[A-Z]*|I5\d{6,}|HLSI.*|D\d{3,})$")


def model_tokens(title: str) -> set[str]:
    """Tokens con pinta de código de producto: mayúsculas + al menos un dígito, len>=3."""
    out = set()
    for tok in MODEL_RE.findall(title or ""):
        core = tok.replace("-", "").replace("/", "").upper()
        if len(core) >= 3 and any(c.isdigit() for c in core) and any(c.isalpha() for c in core):
            if not DOCNUM_RE.match(core):
                out.add(core)
    return out


def main() -> None:
    catalog = json.loads(CAT.read_text(encoding="utf-8"))
    resolved = json.loads(RES.read_text(encoding="utf-8"))
    corpus = json.loads(CORP.read_text(encoding="utf-8"))

    # --- índices del corpus (TODOS los 1012 docs, no solo Notifier/Morley: un doc del portal
    #     puede estar en el corpus etiquetado con otro fabricante)
    idx_exact: dict[str, list[str]] = defaultdict(list)
    idx_norm: dict[str, list[str]] = defaultdict(list)
    idx_loose: dict[str, list[str]] = defaultdict(list)
    idx_rev: dict[str, list[str]] = defaultdict(list)
    idx_lang: dict[str, list[str]] = defaultdict(list)
    for sf in corpus:
        idx_exact[base_name(sf).lower()].append(sf)
        idx_norm[norm(sf)].append(sf)
        idx_loose[norm_loose(sf)].append(sf)
        k = norm_revagnostic(sf)
        if k:
            idx_rev[k].append(sf)
        k2 = lang_agnostic_key(sf)
        if k2:
            idx_lang[k2].append(sf)
    corpus_norms = list(idx_norm.keys())

    # tokens de modelo presentes en el corpus (para "familias a medias")
    corpus_model_tokens: Counter = Counter()
    # vocabulario de product_model normalizado: capta nombres SIN dígitos (NFS Supra, DXc…)
    corpus_pm_norm: Counter = Counter()
    for sf, v in corpus.items():
        toks = model_tokens(sf.upper()) | {
            re.sub(r"[^A-Z0-9]", "", (m or "").upper()) for m in v.get("product_models", [])
        }
        for t in toks:
            if t and len(t) >= 3:
                corpus_model_tokens[t] += 1
        for m in v.get("product_models", []):
            k = re.sub(r"[^a-z0-9]+", "", strip_accents((m or "").lower()))
            if len(k) >= 5:  # >=5 para no disparar con 'id3'/'zxe' dentro de cualquier palabra
                corpus_pm_norm[k] += 1

    records = []
    for e in catalog:
        links = e.get("links") or []
        url = links[0] if links else None
        r = resolved.get(url) if url else None
        fname_raw = (r or {}).get("filename")
        fname = unicodedata.normalize("NFC", fix_mojibake(fname_raw)) if fname_raw else fname_raw
        rec = {
            "site": e["site"],
            "cat": e["cat"],
            "title": e["title"],
            "meta": e.get("meta"),
            "lang": lang_of(e.get("meta", "")),
            "family": family_of(e.get("meta", "")),
            "url": url,
            "filename": fname,
            "filename_raw_header": fname_raw if fname_raw != fname else None,
            "resolve_status": (r or {}).get("status") if r else ("sin enlace" if not url else "no intentado"),
            "resolve_error": (r or {}).get("error") if r else None,
            "filename_source": (r or {}).get("filename_source") if r else None,
            "size_bytes": (r or {}).get("cd_size") or (r or {}).get("content_length"),
        }
        if fname:
            b, n, l = base_name(fname).lower(), norm(fname), norm_loose(fname)
            if b in idx_exact:
                rec["match_tier"], rec["corpus_match"] = "T1_exact", idx_exact[b]
            elif n in idx_norm:
                rec["match_tier"], rec["corpus_match"] = "T2_norm", idx_norm[n]
            elif l in idx_loose:
                rec["match_tier"], rec["corpus_match"] = "T3_revloose", idx_loose[l]
            elif norm_revagnostic(fname) and norm_revagnostic(fname) in idx_rev:
                rec["match_tier"] = "T4_revagnostic"
                rec["corpus_match"] = idx_rev[norm_revagnostic(fname)]
            else:
                rec["match_tier"], rec["corpus_match"] = None, []
                near = difflib.get_close_matches(n, corpus_norms, n=3, cutoff=0.85)
                rec["near_misses"] = [
                    {"corpus_file": idx_norm[k][0], "ratio": round(difflib.SequenceMatcher(None, n, k).ratio(), 3)}
                    for k in near
                ]
                rec["near_miss_top"] = rec["near_misses"][0]["ratio"] if rec["near_misses"] else None
                # ¿tenemos YA el mismo documento en español? -> baja muchísimo la prioridad
                twins = []
                for v in spanish_variants(fname):
                    twins += idx_norm.get(norm(v), [])
                    twins += idx_loose.get(norm_loose(v), [])
                    kk = norm_revagnostic(v)
                    if kk:
                        twins += idx_rev.get(kk, [])
                rec["gemelo_es_en_corpus"] = sorted(set(twins))
                # ¿el mismo documento en CUALQUIER idioma ya en el corpus?
                lk = lang_agnostic_key(fname)
                rec["gemelo_otro_idioma_en_corpus"] = sorted(set(idx_lang.get(lk, [])) - set(twins)) if lk else []
            rec["doc_class"] = doc_class(e["title"], fname)
            # La señal de familia sale del TÍTULO (lleva el nombre de producto);
            # el nombre de fichero suele ser un número interno de documento.
            rec["model_tokens"] = sorted(model_tokens(e["title"]))
            hits = {t: corpus_model_tokens[t] for t in rec["model_tokens"] if corpus_model_tokens.get(t)}
            # 2ª señal: ¿algún product_model del corpus aparece literal en el título?
            tnorm = re.sub(r"[^a-z0-9]+", "", strip_accents((e["title"] or "").lower()))
            for pm, cnt in corpus_pm_norm.items():
                if pm in tnorm:
                    hits[f"pm:{pm}"] = cnt
            rec["family_corpus_hits"] = hits
            rec["family_partial"] = bool(hits)
            rec["family_corpus_docs"] = sum(hits.values())
        records.append(rec)

    # --- dedupe de la lista de adquisición por nombre de fichero normalizado
    missing = [r for r in records if r.get("filename") and r.get("match_tier") is None]
    seen: dict[str, dict] = {}
    for r in missing:
        k = norm(r["filename"])
        if k not in seen:
            r = dict(r)
            r["dup_entries"] = 1
            seen[k] = r
        else:
            seen[k]["dup_entries"] += 1
    missing_u = list(seen.values())

    CLASS_RANK = {
        "manual prog/config/puesta-en-marcha": 0,
        "manual instalacion/uso/conexionado": 1,
        "otro/indeterminado": 2,
        "faq/soporte": 3,
        "datasheet/certificado": 4,
    }
    LANG_RANK = {"es": 0, "multi (incl. es)": 1, "sin declarar": 2, "en": 3}
    for r in missing_u:
        r["prio_score"] = (
            # el gemelo español ya en el corpus domina todo lo demás: es una traducción
            # de algo que YA tenemos -> valor marginal casi nulo para un bot en español
            (1000 if r.get("gemelo_es_en_corpus") else 0)
            + (500 if r.get("gemelo_otro_idioma_en_corpus") else 0)
            + CLASS_RANK.get(r["doc_class"], 9) * 100
            + (0 if r["family_partial"] else 30)
            + LANG_RANK.get(r["lang"], 6) * 5
            + (0 if r["cat"] == "manuales" else 3)
        )
    missing_u.sort(key=lambda r: (r["prio_score"], -r.get("family_corpus_docs", 0), r["title"]))

    matched = [r for r in records if r.get("match_tier")]
    unresolved = [r for r in records if not r.get("filename")]
    # T3/T4: el documento YA está en el corpus, pero el fichero del portal es otra
    # edición/revisión -> no es adquisición, es actualización.
    reedition = [r for r in matched if r["match_tier"] in ("T3_revloose", "T4_revagnostic")]

    # --- vista inversa: docs Notifier/Morley del corpus que el catálogo NO alcanza
    reached = {m for r in matched for m in r["corpus_match"]}
    corpus_nm = [sf for sf, v in corpus.items() if v["manufacturer"] in ("Notifier", "Morley")]
    corpus_nm_unreached = sorted(sf for sf in corpus_nm if sf not in reached)

    summary = {
        "catalogo_entradas": len(catalog),
        "catalogo_enlaces_unicos": len({r["url"] for r in records if r["url"]}),
        "entradas_sin_enlace": sum(1 for r in records if not r["url"]),
        "resueltos_a_nombre_de_fichero": len(matched) + len(missing),
        "ficheros_unicos_resueltos": len({norm(r["filename"]) for r in records if r.get("filename")}),
        "casan_con_corpus": len(matched),
        "casan_con_corpus_ficheros_unicos": len({norm(r["filename"]) for r in matched}),
        "casan_por_tier": dict(Counter(r["match_tier"] for r in matched)),
        "cobertura_crawl_por_lote": {
            f"{site}/{cat}": {
                "entradas": sum(1 for r in records if r["site"] == site and r["cat"] == cat),
                "resueltas": sum(
                    1 for r in records if r["site"] == site and r["cat"] == cat and r.get("filename")
                ),
            }
            for site, cat in sorted({(r["site"], r["cat"]) for r in records})
        },
        "no_en_corpus_entradas": len(missing),
        "no_en_corpus_ficheros_unicos": len(missing_u),
        "sin_resolver": len(unresolved),
        "sin_resolver_motivos": dict(Counter(str(r["resolve_error"] or r["resolve_status"]) for r in unresolved)),
        "corpus_docs_totales": len(corpus),
        "corpus_docs_notifier": sum(1 for v in corpus.values() if v["manufacturer"] == "Notifier"),
        "corpus_docs_morley": sum(1 for v in corpus.values() if v["manufacturer"] == "Morley"),
        "corpus_docs_alcanzados_por_el_cruce": len(reached),
        "corpus_nm_no_alcanzados": len(corpus_nm_unreached),
        "edicion_posiblemente_distinta_T3_T4": len(reedition),
        "adquisicion_con_near_miss_>=0.85": sum(1 for r in missing_u if r.get("near_miss_top")),
        "adquisicion_neta": sum(
            1 for r in missing_u
            if not r.get("gemelo_es_en_corpus") and not r.get("gemelo_otro_idioma_en_corpus")
        ),
        "adquisicion_traduccion_de_algo_que_ya_tenemos": sum(
            1 for r in missing_u
            if r.get("gemelo_es_en_corpus") or r.get("gemelo_otro_idioma_en_corpus")
        ),
        "adquisicion_por_sitio": dict(Counter(r["site"] for r in missing_u)),
        "adquisicion_por_clase": dict(Counter(r["doc_class"] for r in missing_u)),
        "adquisicion_por_idioma": dict(Counter(r["lang"] for r in missing_u)),
        "adquisicion_por_categoria": dict(Counter(r["cat"] for r in missing_u)),
    }

    OUT_JSON.write_text(
        json.dumps(
            {
                "summary": summary,
                "criterio_cruce": {
                    "T1_exact": "nombre sin extensión, case-insensitive",
                    "T2_norm": "minúsculas + sin acentos + solo alfanuméricos",
                    "T3_revloose": "T2 tras podar sufijos de revisión finales (rvNN/revX/vNN/issue N/_NN/_X/_copia…)",
                    "no_se_poda": "sufijos de idioma (_ES/_EN/_SP) — versión ES y EN son documentos distintos",
                    "corpus_comparado": "los 1012 source_file de chunks_v2 (no solo los 705 Notifier/Morley)",
                },
                "adquisicion": missing_u,
                "matched": matched,
                "unresolved": unresolved,
                "reedition_T3_T4": reedition,
                "corpus_nm_no_alcanzados": corpus_nm_unreached,
            },
            ensure_ascii=False,
            indent=1,
        ),
        encoding="utf-8",
    )
    write_md(summary, missing_u, matched, reedition, unresolved, corpus_nm_unreached, corpus)
    print(json.dumps(summary, ensure_ascii=False, indent=1))


# --------------------------------------------------------------------------- informe MD
def md_url(u: str | None) -> str:
    """66 URLs (las directas de Morley) llevan espacios: sin escapar, rompen el enlace MD."""
    if not u:
        return ""
    return u.replace(" ", "%20").replace("(", "%28").replace(")", "%29")


def _row(r: dict, i: int) -> str:
    fam = (r.get("family") or "").replace("|", "/")
    tit = (r["title"] or "").replace("|", "/").strip()
    fn = (r["filename"] or "").replace("|", "/")
    flag = "sí" if r.get("family_partial") else "no"
    size = r.get("size_bytes")
    try:
        size = f"{int(size)/1024:.0f} KB" if size else "?"
    except (TypeError, ValueError):
        size = "?"
    return (
        f"| {i} | {tit} | `{fn}` | {r['lang']} | {fam} | {flag} | {size} | "
        f"[descargar]({md_url(r['url'])}) |"
    )


# Gemelos verificados A MANO contra el corpus (s303). Ninguna regla automática los empareja:
# se declaran explícitamente en el informe para no inflar la lista de adquisición neta.
MANUAL_TWINS = [
    ("1998M0902_FS20X_PT-BR54-10_PT-BR_RevB_20July2015.pdf",
     "1998M0902_FS20X_ES_AR54-10_ES_AR_RevB_20July2015",
     "MISMO documento, edición ES-AR ya en corpus → traducción, no adquisición"),
    ("DXc_Product manual_Portuguese.pdf / DXc_Manual de utilizador.pdf",
     "DXc_Manual de configuracion · DXc_Manual de usuario",
     "el corpus tiene el manual DXc en español (config + usuario) → probable traducción"),
    ("0034-033-01 Guide F5000 PT.pdf / 0034-034-01 Manual F5000 PT.pdf",
     "0044-033-01 Guia F5000 · F5K-2H-UserGuide-SPANISH_Manual F5000",
     "el corpus tiene guía y manual F5000 en español (otro nº de parte) → probable traducción"),
    ("3- TG-Honeywell_Technician_Eng_v9.0.pdf",
     "Tg-Honeywell_Tecnico",
     "versión inglesa; el corpus tiene la española (edición anterior) → baja prioridad"),
    ("MNDT105P.pdf (ya en 2.B)",
     "MNDT105_A",
     "el gemelo ES lleva sufijo `_A`; sólo lo empareja el nivel T3"),
]

HDR = (
    "| # | Título | Fichero | Idioma | Familia | ¿fam. ya a medias? | Tamaño | URL |\n"
    "|---|---|---|---|---|---|---|---|"
)


def write_md(summary, missing_u, matched, reedition, unresolved, corpus_nm_unreached, corpus) -> None:
    s = summary
    resueltos = s["resueltos_a_nombre_de_fichero"]
    intentados = s["catalogo_enlaces_unicos"]
    pend = sum(1 for r in unresolved if r["resolve_status"] == "no intentado")
    pct = 100 * (intentados - pend) / intentados if intentados else 0

    L = []
    A = L.append
    A("# s303 — Cruce catálogo de portales (Notifier / Morley) × corpus `chunks_v2`")
    A("")
    A(
        f"> Generado por `scripts/s303_cross_portal_corpus.py`. Resolución título→fichero por "
        f"`scripts/s303_resolve_portal_filenames.py` (HEAD secuencial, 3 s entre peticiones, "
        f"runbook `docs/CORPUS_NOTIFIER_MORLEY.md` §2)."
    )
    A("")
    A(f"**Cobertura del crawl: {intentados - pend}/{intentados} enlaces únicos ({pct:.1f}%).**")
    if pend:
        A("")
        A(
            f"⚠️ **RESULTADO PARCIAL** — quedan {pend} enlaces sin intentar. Las cifras de abajo "
            f"son las del {pct:.1f}% barrido, no del catálogo completo."
        )
    A("")
    A("## 1. Cifras de cabecera")
    A("")
    A("| | |")
    A("|---|---|")
    A(f"| Entradas del catálogo cosechado | {s['catalogo_entradas']} |")
    A(f"| Enlaces de descarga únicos | {s['catalogo_enlaces_unicos']} |")
    A(f"| **Resueltos a nombre de fichero real** | **{resueltos}** entradas ({s['ficheros_unicos_resueltos']} ficheros únicos) |")
    A(f"| Casan con el corpus | {s['casan_con_corpus']} entradas ({s['casan_con_corpus_ficheros_unicos']} ficheros únicos) |")
    A(f"| └ de ellos, otra edición/revisión (T3/T4) | {s['edicion_posiblemente_distinta_T3_T4']} |")
    A(f"| **NO están en el corpus = lista de adquisición** | **{s['no_en_corpus_ficheros_unicos']} ficheros únicos** ({s['no_en_corpus_entradas']} entradas) |")
    A(f"| └ **adquisición NETA** (el corpus no lo tiene en ningún idioma) | **{s['adquisicion_neta']}** |")
    A(f"| └ traducción de un documento que ya tenemos | {s['adquisicion_traduccion_de_algo_que_ya_tenemos']} |")
    A(f"| Sin resolver | {s['sin_resolver']} |")
    A(f"| Docs del corpus alcanzados por el cruce | {s['corpus_docs_alcanzados_por_el_cruce']} / {s['corpus_docs_totales']} |")
    A(f"| Docs Notifier+Morley del corpus NO alcanzados | {s['corpus_nm_no_alcanzados']} / 705 |")
    A("")
    A("**Cobertura del crawl por lote** (`manuales` = vigentes · `manuales-des` = descatalogados):")
    A("")
    A("| Lote | Entradas | Resueltas |")
    A("|---|---|---|")
    for k, v in s["cobertura_crawl_por_lote"].items():
        A(f"| `{k}` | {v['entradas']} | {v['resueltas']} |")
    A("")
    A("**Motivos de «sin resolver»:**")
    A("")
    for k, v in sorted(s["sin_resolver_motivos"].items(), key=lambda x: -x[1]):
        A(f"- `{k}` — {v}")
    A("")
    A("**Reparto de la lista de adquisición:**")
    A("")
    A(f"- por sitio: {s['adquisicion_por_sitio']}")
    A(f"- **neta vs traducción**: {s['adquisicion_neta']} netos · "
      f"{s['adquisicion_traduccion_de_algo_que_ya_tenemos']} traducciones de algo ya presente")
    A(f"- por clase de documento: {s['adquisicion_por_clase']}")
    A(f"- por idioma: {s['adquisicion_por_idioma']}")
    A(f"- por categoría del portal: {s['adquisicion_por_categoria']} (`manuales` = vigente, `manuales-des` = descatalogado)")
    A("")
    A("### Criterio de cruce (declarado)")
    A("")
    A("Se compara el nombre de fichero servido por el portal contra los `source_file` **de los "
      f"{s['corpus_docs_totales']} documentos** de `chunks_v2` (no solo los 705 de Notifier/Morley: "
      "un doc del portal puede estar en el corpus etiquetado con otro fabricante).")
    A("")
    A("| Nivel | Regla | Lectura |")
    A("|---|---|---|")
    A("| **T1 exact** | nombre sin extensión, insensible a mayúsculas | mismo fichero |")
    A("| **T2 norm** | minúsculas + sin acentos + **solo alfanuméricos** (quita `-`, `_`, espacios, `.`) | mismo fichero, `MN-DT-200` ≡ `MNDT200` |")
    A("| **T3 revloose** | T2 tras podar sufijos de revisión FINALES (`rvNN`, `revX`, `vNN`, `issue N`, `_X`, `_copia`, `_lr`…) | mismo doc, edición quizá distinta |")
    A("| **T4 revagnostic** | quita **cualquier** token de revisión/fecha (`rev 5`, `09-07-2026`, `RevB`, `20July2015`, año suelto) y compara | mismo doc, **otra edición** |")
    A("| sin match | — | **candidato de adquisición** |")
    A("")
    A("Sobre cada candidato sin match se corre además una **detección de gemelo**, que NO es un "
      "nivel de cruce (el fichero sigue sin estar en el corpus) sino una anotación de valor:")
    A("")
    A("- `gemelo_es_en_corpus` — el mismo documento **en español** ya está en el corpus. Dos "
      "reglas, ambas verificadas contra el corpus: (1) el sufijo `P` pegado al número de "
      "documento HLSI marca la versión portuguesa (`MNDT250P` ↔ `MNDT250`, `MADT190P_02` ↔ "
      "`MADT190_02`); (2) en la gama de part-numbers `997-xxx-NNN-`, `-007-` es portugués y "
      "`-005-` español (comprobado con `997-670-007-3_Operating_PT` / "
      "`997-670-005-3_Operating_ES` y el par equivalente de `997-671`).")
    A("- `gemelo_otro_idioma_en_corpus` — quitando **todos** los marcadores de idioma a ambos "
      "lados, el nombre coincide con un documento del corpus (`Manual SIMEI-HLSI_FR-PT` ↔ "
      "`Manual SIMEI-HLSI_SP-EN`). Puede ser la misma edición española cuando es el nombre del "
      "corpus el que lleva el marcador (`HLSI-MA-025_rv03 Guia Rapida NFS_Supra` ↔ "
      "`HLSI-MA-025 Guia Rapida NFS_Supra_ES`).")
    A("")
    A("Esa detección **no elimina nada de la lista**: mueve el candidato al bloque 2.B.")
    A("")
    A("Decisiones explícitas de la normalización:")
    A("")
    A("- **NO se podan los sufijos de idioma en los niveles T1–T4** (`_ES`, `_EN`, `_SP`, `_PT`): "
      "la versión española y la inglesa del mismo manual son ficheros **distintos** y podarlos "
      "habría hecho desaparecer candidatos legítimos del cruce. El idioma se trata aparte, en la "
      "detección de gemelo, que anota sin borrar.")
    A("- **NO se poda el sufijo `_NN` final.** En la nomenclatura HLSI es un **sub-número de "
      "documento**, no una revisión — verificado en el corpus: `MADT190_01`…`MADT190_15` son **13 "
      "documentos distintos** (`product_model` = ID²NET / ID3000 / LIB3000 / ID-CRA / PSU7A…). "
      "Una versión previa de este cruce sí lo podaba y fabricó un match falso "
      "(`MADT190P_02` → `MADT190P_01_C`), que habría borrado un candidato real de la lista.")
    A("- **Reparación de mojibake obligatoria.** Las cabeceras HTTP se decodifican en latin-1 "
      "(RFC 9110) pero el portal envía el nombre en UTF-8: `programación` llega como "
      "`programacioÌ\\x81n`. Sin reparar el round-trip latin-1→utf-8, **todo fichero con acento "
      "falla el cruce y aparece como falso candidato de adquisición** "
      f"({sum(1 for r in matched + missing_u if r.get('filename_raw_header'))} ficheros afectados aquí).")
    A("")

    # ------------------------------------------------------------------ 2. adquisición
    neta = [r for r in missing_u if not r.get("gemelo_es_en_corpus") and not r.get("gemelo_otro_idioma_en_corpus")]
    trad = [r for r in missing_u if r.get("gemelo_es_en_corpus") or r.get("gemelo_otro_idioma_en_corpus")]

    A("## 2. Lista de adquisición")
    A("")
    A(f"**{len(missing_u)} ficheros del portal no están en el corpus**, pero no todos valen lo "
      f"mismo: **{len(trad)} son la traducción de un documento que YA tenemos** (típicamente el "
      "sufijo `P` = portugués sobre el mismo número de documento HLSI: `MNDT250P` ↔ `MNDT250`). "
      f"La adquisición **neta** son **{len(neta)} ficheros** — es la lista 2.A.")
    A("")
    A("Orden dentro de cada bloque: (a) manuales de programación/configuración/puesta en marcha "
      "por delante de instalación/uso, y estos por delante de hojas de datos y FAQ · (b) familias "
      "de las que el corpus ya tiene algo (columna «¿fam. ya a medias?») · (c) español > "
      "multilingüe > sin declarar > otros idiomas · (d) vigente > descatalogado.")
    A("")
    order = [
        ("manual prog/config/puesta-en-marcha", "Manuales de PROGRAMACIÓN · configuración · puesta en marcha · licencias — MÁXIMA PRIORIDAD"),
        ("manual instalacion/uso/conexionado", "Manuales de instalación · uso · conexionado · guías rápidas"),
        ("otro/indeterminado", "Documentos sin señal clara en el título"),
        ("faq/soporte", "FAQ / notas de soporte"),
        ("datasheet/certificado", "Hojas de datos · certificados · catálogos"),
    ]

    A(f"### 2.A — ADQUISICIÓN NETA: {len(neta)} documentos que el corpus no tiene en ningún idioma")
    A("")
    if not neta:
        A("_(vacía)_")
    i = 0
    k = 0
    for cls, head in order:
        rows = [r for r in neta if r["doc_class"] == cls]
        if not rows:
            continue
        k += 1
        A(f"#### 2.A.{k} {head} — {len(rows)}")
        A("")
        A(HDR)
        for r in rows:
            i += 1
            A(_row(r, i))
        A("")

    A(f"### 2.B — BAJA PRIORIDAD: {len(trad)} traducciones de documentos que ya están en el corpus")
    A("")
    A("Mismo documento, otra edición idiomática. Para un bot que responde en español a técnicos "
      "españoles el valor marginal es casi nulo; se listan por completitud y porque alguna podría "
      "servir si la versión española que tenemos está incompleta o mal extraída.")
    A("")
    if trad:
        A("| # | Título | Fichero | Idioma | Ya en el corpus como | URL |")
        A("|---|---|---|---|---|---|")
        for j, r in enumerate(trad, 1):
            tw = r.get("gemelo_es_en_corpus") or r.get("gemelo_otro_idioma_en_corpus")
            A(f"| {j} | {(r['title'] or '').replace('|', '/')[:80]} | `{r['filename']}` | "
              f"{r['lang']} | `{'`, `'.join(tw)}` | [descargar]({md_url(r['url'])}) |")
    else:
        A("_(ninguna)_")
    A("")

    # ------------------------------------------------------------------ 3. reediciones
    A("## 3. Anexo — ya en el corpus pero el portal sirve OTRA edición (T3/T4)")
    A("")
    A("No son adquisición (el documento ya está), son **actualización**: merece la pena "
      "re-descargar y re-ingerir si la edición del portal es más reciente.")
    A("")
    if reedition:
        A("| Fichero en el portal | Doc en el corpus | Nivel | URL |")
        A("|---|---|---|---|")
        for r in reedition:
            A(f"| `{r['filename']}` | `{'`, `'.join(r['corpus_match'])}` | {r['match_tier']} | [descargar]({md_url(r['url'])}) |")
    else:
        A("_(ninguno detectado)_")
    A("")

    # ------------------------------------------------------------------ 4. incertidumbre
    A("## 4. Falsos positivos y falsos negativos del cruce (incertidumbre declarada)")
    A("")
    A("### 4.1 Candidatos con un vecino MUY parecido en el corpus")
    A("")
    A("Estos entran en la lista de adquisición, pero su nombre normalizado se parece ≥0.85 "
      "(difflib) a un documento que YA tenemos. Puede ser el mismo documento renombrado "
      "(→ falso candidato) o un producto hermano (→ candidato legítimo). **Requieren ojo humano.** "
      "Aviso: en códigos cortos tipo `MNDT1102` el ratio de difflib es engañosamente alto "
      "(`MNDT1102` vs `MNDT110` = 0.93 y son documentos distintos).")
    A("")
    nm = [r for r in missing_u if r.get("near_miss_top")]
    if nm:
        A("| Bloque | Candidato del portal | Vecino en el corpus | ratio |")
        A("|---|---|---|---|")
        for r in sorted(nm, key=lambda x: -x["near_miss_top"]):
            n0 = r["near_misses"][0]
            blk = "2.B" if (r.get("gemelo_es_en_corpus") or r.get("gemelo_otro_idioma_en_corpus")) else "2.A"
            A(f"| {blk} | `{r['filename']}` | `{n0['corpus_file']}` | {n0['ratio']} |")
    else:
        A("_(ninguno)_")
    A("")
    A("### 4.2 Gemelos que el cruce NO detecta — verificados a mano")
    A("")
    A("Casos que **ninguna regla automática empareja** pero que al mirar el corpus a mano sí "
      "tienen equivalente. Los cuatro primeros siguen en 2.A y, en rigor, deberían leerse como "
      "2.B: **la adquisición neta real es de 43 menos ~6 ficheros**. Se declaran uno a uno en "
      "lugar de añadir más heurística frágil.")
    A("")
    A("| Candidato en 2.A | Equivalente encontrado a mano en el corpus | Lectura |")
    A("|---|---|---|")
    for cand, twin, read in MANUAL_TWINS:
        A(f"| `{cand}` | `{twin}` | {read} |")
    A("")
    A("El caso `3- TG-Honeywell_Tecnico_v9.0` es el contrario y por eso encabeza 2.A: no es una "
      "traducción, es la **versión 9 de un manual técnico del que el corpus tiene una edición "
      "anterior sin numerar**. El prefijo `3- ` y el `_v9.0` impiden que T4 lo empareje.")
    A("")
    A("### 4.3 Límites conocidos del criterio")
    A("")
    A("1. **El cruce es por NOMBRE DE FICHERO, no por contenido.** Si el mismo PDF vive en el "
      "corpus bajo un nombre completamente distinto (p. ej. descargado en su día de otra fuente "
      "o renombrado a mano), este cruce lo declara «no en corpus» y es un **falso candidato**. "
      "No se ha hecho ninguna comparación de contenido ni de hash.")
    A(f"2. **{s['corpus_nm_no_alcanzados']} de los 705 documentos Notifier/Morley del corpus no "
      "los alcanza ningún fichero del catálogo.** Eso acota el tamaño del problema anterior: "
      "buena parte del corpus procede de nombres que estos portales hoy no sirven "
      "(descatalogados retirados, material de distribuidor, FAQ del gestor de contenidos, "
      "renombrados). Cualquiera de esos podría ser el gemelo renombrado de un candidato.")
    A("3. **Documentos multilingües.** Un `_Multi` del portal puede contener el español que ya "
      "tenemos en un PDF monolingüe con otro nombre. El cruce no lo detecta.")
    A("4. **La clase del documento se infiere del TÍTULO** (palabras clave prog/config vs hoja "
      "de características). Los títulos escuetos caen en «sin clasificar» — la prioridad de esa "
      "sección es orientativa, no verificada.")
    A("5. **«¿fam. ya a medias?»** se calcula con tokens con pinta de código de producto "
      "extraídos del título, contrastados contra los nombres de fichero y el `product_model` del "
      "corpus. Es una heurística léxica: no distingue `ZXSe` de `ZXe`, ni sabe que FAAST LT-200 "
      "y FAAST 7100 son familias distintas.")
    A("")

    # ------------------------------------------------------------------ 5. no verificado
    A("## 5. Lo que NO se ha verificado")
    A("")
    A("- **No se ha descargado ningún PDF.** Solo se leyeron cabeceras (HEAD). Por tanto **no "
      "está verificado que el fichero servido sea legible, ni que su contenido corresponda al "
      "título del índice**, ni su número de páginas.")
    if pend:
        A(f"- **{pend} enlaces del catálogo quedaron sin intentar** (crawl parcial al {pct:.1f}%). "
          "Todo lo que hubiera ahí es desconocido, ni presente ni ausente.")
    A(f"- **{s['entradas_sin_enlace']} entradas del catálogo no traían enlace de descarga** en la "
      "cosecha: existen en el índice, pero su fichero no se puede resolver sin re-visitar el "
      "portal. Se listan porque alguna es material de interés:")
    nolink = [r for r in unresolved if r["resolve_status"] == "sin enlace"]
    if nolink:
        A("")
        A("| Sitio | Cat. | Título | Meta |")
        A("|---|---|---|---|")
        for r in nolink:
            A(f"| {r['site']} | {r['cat']} | {(r['title'] or '').replace('|', '/')} | {r['meta']} |")
        A("")
    A("- **Licencia**: accesible ≠ redistribuible. Los términos de ambos portales no se han "
      "revisado (mismo límite declarado en el runbook §6).")
    A("- **Vigencia del enlace**: los 659 enlaces de Notifier son del componente ZOO y llevan "
      "un hash por ítem — si el portal regenera contenidos, caducan. Los 178 de Morley son URLs "
      "directas al fichero y son más estables, pero dependen de que no se reorganice la carpeta. "
      "La lista es un activo CON FECHA (7-ago-2026).")
    A("")
    A("### Artefactos y reproducibilidad")
    A("")
    A(f"- `evals/s303_cruce_portales_corpus_v1.json` — datos completos: los "
      f"{s['casan_con_corpus']} que sí casan, los {s['no_en_corpus_ficheros_unicos']} candidatos "
      "con todos sus campos, los no resueltos y los 131 docs del corpus que el catálogo no alcanza.")
    A("- `data/catalog_portales/s303_resolved_filenames_v1.json` — la resolución "
      "URL→nombre-de-fichero de los 835 enlaces (cabeceras crudas, tamaños, método). **`data/` "
      "está en `.gitignore`**: este fichero vive solo en disco, no en el repo. Reconstruirlo "
      "cuesta 45 min de crawl.")
    A("- `data/catalog_portales/s303_corpus_source_files.json` — foto de los 1012 `source_file` "
      "de `chunks_v2` con `manufacturer`/`doc_type`/`language`/`product_model` (también fuera del repo).")
    A("- Rehacer el cruce sin volver a tocar los portales: "
      "`python scripts/s303_cross_portal_corpus.py` (solo lee ficheros locales).")
    A("")

    OUT_MD.write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    main()
