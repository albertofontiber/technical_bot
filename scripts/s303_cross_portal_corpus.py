"""s303 — cruza el catálogo de los portales Notifier/Morley contra el corpus (chunks_v2).

Entradas
  data/catalog_portales/s303_portales_notifier_morley_v1.json   (844 entradas cosechadas)
  data/catalog_portales/s303_resolved_filenames_v1.json         (url -> nombre de fichero real)
  data/catalog_portales/s303_corpus_source_files.json           (source_file distintos de chunks_v2)

Salidas
  evals/s303_cruce_portales_corpus_v1.json
  evals/s303_cruce_portales_corpus_v1.md

Criterio de cruce — 3 niveles, declarados (de más a menos seguro):
  T1 EXACT    nombre sin extensión, insensible a mayúsculas
  T2 NORM     minúsculas + sin acentos + SOLO alfanuméricos (quita '-', '_', ' ', '.')
  T3 REVLOOSE T2 tras podar sufijos de revisión finales: rvNN / revNN / revX / vNN /
              issue N / _NN / _X (letra suelta) / _copia|_lr|_prelim…
  Los sufijos de IDIOMA (_ES/_EN/_SP/_ENG) NO se podan a propósito: la versión española y
  la inglesa del mismo manual son documentos DISTINTOS y ambos pueden interesar.
Un fichero del portal que no case en ninguno de los 3 niveles = candidato de adquisición.
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
REVDATE_TOKENS = [
    r"\d{1,2}[\-/_\.]\d{1,2}[\-/_\.]\d{2,4}",  # 09-07-2025
    r"\d{1,2}[\-/_\.]\d{4}",  # 04-2025
    r"\d{1,2}[a-z]{3,9}\d{4}",  # 20july2015
    r"\b(?:rev|revision|rv|issue|iss|ed|edicion)[\s_\-\.]*\d{1,3}[a-z]?\b",
    r"\b(?:rev|revision|rv|issue|iss)[\s_\-\.]*[a-z]\b",
    r"\b(?:lr|hr|copia|copy|prelim|preliminar|draft)\b",
    r"\b(19|20)\d{2}\b",  # año suelto
]
REVDATE_RE = re.compile("|".join(REVDATE_TOKENS))


def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def base_name(s: str) -> str:
    # NFC: el portal sirve algunos nombres en forma DESCOMPUESTA (p.ej. "programacio" + U+0301);
    # sin esto, T1 fallaría contra el corpus por una diferencia invisible.
    return unicodedata.normalize("NFC", EXT_RE.sub("", (s or "").strip()).strip())


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


# ---------------------------------------------------------------- clasificación de valor
PROG_KW = [
    "programacion",
    "programming",
    "configuracion",
    "configuration",
    "puesta en marcha",
    "commissioning",
    "instalacion",
    "installation",
    "manual de usuario",
    "user manual",
    "operating",
    "operacion",
    "mantenimiento",
    "maintenance",
    "manual tecnico",
    "technical manual",
    "guia rapida",
    "quick",
    "software",
    "menu",
    "puesta",
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
    "dop",
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
        return "manual (prog/config/instal)"
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
    for sf in corpus:
        idx_exact[base_name(sf).lower()].append(sf)
        idx_norm[norm(sf)].append(sf)
        idx_loose[norm_loose(sf)].append(sf)
        k = norm_revagnostic(sf)
        if k:
            idx_rev[k].append(sf)
    corpus_norms = list(idx_norm.keys())

    # tokens de modelo presentes en el corpus (para "familias a medias")
    corpus_model_tokens: Counter = Counter()
    for sf, v in corpus.items():
        toks = model_tokens(sf.upper()) | {
            re.sub(r"[^A-Z0-9]", "", (m or "").upper()) for m in v.get("product_models", [])
        }
        for t in toks:
            if t and len(t) >= 3:
                corpus_model_tokens[t] += 1

    records = []
    for e in catalog:
        links = e.get("links") or []
        url = links[0] if links else None
        r = resolved.get(url) if url else None
        fname = (r or {}).get("filename")
        rec = {
            "site": e["site"],
            "cat": e["cat"],
            "title": e["title"],
            "meta": e.get("meta"),
            "lang": lang_of(e.get("meta", "")),
            "family": family_of(e.get("meta", "")),
            "url": url,
            "filename": fname,
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
                # ratio muy alto = casi seguro el MISMO documento en otra revisión/fecha:
                # no es "no lo tenemos", es "tenemos una revisión anterior".
                rec["probable_revision_nueva"] = bool(near and rec["near_misses"][0]["ratio"] >= 0.90)
            rec["doc_class"] = doc_class(e["title"], fname)
            # La señal de familia sale del TÍTULO (lleva el nombre de producto);
            # el nombre de fichero suele ser un número interno de documento.
            rec["model_tokens"] = sorted(model_tokens(e["title"]))
            rec["family_partial"] = any(corpus_model_tokens.get(t, 0) > 0 for t in rec["model_tokens"])
            rec["family_corpus_docs"] = sum(corpus_model_tokens.get(t, 0) for t in rec["model_tokens"])
            rec["family_corpus_hits"] = {
                t: corpus_model_tokens[t] for t in rec["model_tokens"] if corpus_model_tokens.get(t)
            }
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

    CLASS_RANK = {"manual (prog/config/instal)": 0, "otro/indeterminado": 1, "faq/soporte": 2, "datasheet/certificado": 3}
    LANG_RANK = {"es": 0, "multi (incl. es)": 1, "sin declarar": 2, "en": 3}
    for r in missing_u:
        r["prio_score"] = (
            CLASS_RANK.get(r["doc_class"], 9) * 100
            + (0 if r["family_partial"] else 30)
            + LANG_RANK.get(r["lang"], 6) * 5
            + (0 if r["cat"] == "manuales" else 3)
        )
    missing_u.sort(key=lambda r: (r["prio_score"], -r.get("family_corpus_docs", 0), r["title"]))

    matched = [r for r in records if r.get("match_tier")]
    unresolved = [r for r in records if not r.get("filename")]

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
        "casan_por_tier": dict(Counter(r["match_tier"] for r in matched)),
        "no_en_corpus_entradas": len(missing),
        "no_en_corpus_ficheros_unicos": len(missing_u),
        "sin_resolver": len(unresolved),
        "sin_resolver_motivos": dict(Counter(str(r["resolve_error"] or r["resolve_status"]) for r in unresolved)),
        "corpus_docs_totales": len(corpus),
        "corpus_docs_notifier": sum(1 for v in corpus.values() if v["manufacturer"] == "Notifier"),
        "corpus_docs_morley": sum(1 for v in corpus.values() if v["manufacturer"] == "Morley"),
        "corpus_docs_alcanzados_por_el_cruce": len(reached),
        "corpus_nm_no_alcanzados": len(corpus_nm_unreached),
        "adquisicion_probable_revision_nueva": sum(1 for r in missing_u if r.get("probable_revision_nueva")),
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
                "corpus_nm_no_alcanzados": corpus_nm_unreached,
            },
            ensure_ascii=False,
            indent=1,
        ),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
