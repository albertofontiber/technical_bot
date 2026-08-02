#!/usr/bin/env python3
"""s294_siempre_census.py — censo OUT-OF-SAMPLE del gatillo compuesto «siempre» (L3 v2).

Cierra de una pasada cuatro exigencias que el dúo puso a la v2 (DEC-171):
  **F4** censo OUT-OF-SAMPLE — el de s292 era in-sample (la vista servida de los 39
        golds ≈1,6% del corpus). Aquí se barre TODO el corpus.
  **F5** ES/EN — el léxico MANDATORY se declara CERRADO BILINGÜE; s292 solo midió ES.
  **F6** lista CERRADA de imperativos en vez del patrón morfológico de clase abierta
        (que era el que daba 69% FP). Modo `discover` la deriva de los datos; modo
        `census` la congela y mide con ella.
  **F3** integridad de span — el apéndice cita VERBATIM: una cita decapitada en un
        aviso de SEGURIDAD rompe el contrato de fuente. Cada captura se audita.

**F7 (adjudicación ciega)**: este script NO adjudica. Emite las capturas con su
taxonomía de defecto de span y un campo `adjudicacion: null` para que las juzgue
alguien que no sea el autor (Alberto o el cross-model), con la taxonomía de «espurio»
pre-registrada ABAJO y fijada ANTES de mirar filas.

Uso:  python scripts/s294_siempre_census.py discover [limite]
      python scripts/s294_siempre_census.py census   [limite]
Salidas: evals/s294_siempre_discovery_v1.json · evals/s294_siempre_census_v1.json
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from collections import Counter

os.environ.setdefault("CHUNKS_TABLE", "chunks_v2")
sys.path.insert(0, os.getcwd())

import httpx  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(os.getcwd(), ".env"), override=False)

from src.config import SUPABASE_URL, SUPABASE_SERVICE_KEY  # noqa: E402
from src.rag.mp_lexicon import sentence_spans  # noqa: E402  (mismo cortador que producción)

MODE = sys.argv[1] if len(sys.argv) > 1 else "discover"
LIMIT = int(sys.argv[2]) if len(sys.argv) > 2 else 4000
TABLE = os.environ["CHUNKS_TABLE"]

# ── TAXONOMÍA DE «ESPURIO» — PRE-REGISTRADA (F7), fijada antes de ver filas ──────
# Una captura es ESPURIA si cae en cualquiera de estas clases. El adjudicador ciego
# marca la clase; la regla de daño es: CUALQUIER fila espuria ⇒ STOP del lever.
SPURIOUS_TAXONOMY = {
    "condicional": "«siempre y cuando» / «siempre que» — no es obligación, es condición",
    "descriptivo": "describe conducta del equipo, no instruye al técnico "
                   "(«el LED permanece siempre fijo», «siempre recibe alimentación»)",
    "nota_de_diseno": "comentario editorial/de diseño del manual, no obligación operativa",
    "fuera_de_dominio": "obligación de otro circuito/producto que la pregunta no cubre "
                        "(clase F8 del dúo: topología confundible = SEGURIDAD)",
    "span_roto": "la cita verbatim no es utilizable: decapitada, fusionada o fragmento",
    "duplicado": "la misma obligación ya emitida por otro átomo del mismo fragmento",
}

# ── Formas del gatillo ───────────────────────────────────────────────────────────
# Exclusión dura del condicional, en ambas variantes.
RX_COND_ES = re.compile(r"\bsiempre\s+(?:y\s+cuando|que)\b", re.IGNORECASE)
RX_SIEMPRE = re.compile(r"\bsiempre\b", re.IGNORECASE)
RX_ALWAYS = re.compile(r"\balways\b", re.IGNORECASE)

# B · deóntico reforzado (NO necesita lista cerrada: el deóntico ya es cerrado)
RX_DEONTIC_ES = re.compile(
    r"\b(?:debe|deben|debera|deberan|deberá|deberán|tiene\s+que|tienen\s+que|hay\s+que)\b",
    re.IGNORECASE,
)
RX_DEONTIC_EN = re.compile(r"\b(?:must|shall)\b", re.IGNORECASE)

# A · imperativo de LISTA CERRADA (F6).  Se deriva en modo `discover` y se congela
# aquí; vacía = el modo census aborta antes que inventarla.
# CONGELADA desde el modo `discover` sobre los 1.197 chunks del corpus con
# «siempre»/«always»: cada entrada está OBSERVADA abriendo una oración con el adverbio
# adyacente (n≥2), no inventada.  Se incluye la variante plural de cortesía cuando la
# forma singular está observada (misma conjugación, coste cero de superficie).
CLOSED_IMPERATIVES_ES: tuple[str, ...] = (
    "asegurese", "asegúrese", "asegurense", "asegúrense",
    "utilice", "utilicen", "use", "usen",
    "configure", "configuren", "desconecte", "desconecten",
    "coloque", "coloquen", "lleve", "lleven", "consulte", "consulten",
    "pruebe", "prueben", "presione", "presionen", "tenga", "tengan",
    "tome", "tomen", "revise", "revisen", "considere", "consideren",
    "lea", "lean", "preste", "presten", "siga", "sigan", "cumpla", "cumplan",
    "confirme", "confirmen", "seleccione", "seleccionen", "obtenga", "obtengan",
)
CLOSED_IMPERATIVES_EN: tuple[str, ...] = (
    "disconnect", "connect", "use", "switch", "turn", "check", "verify", "ensure",
    "install", "replace", "keep", "remove", "wear", "refer", "isolate", "power",
    "read", "follow", "test", "select", "confirm", "make",
)
# El adverbio puede ABRIR la oración y el imperativo seguirle: es el orden canónico en
# inglés («Always disconnect…») y frecuente en español («Siempre desconecte…»).  s292
# solo medía verbo-primero, así que el inglés quedaba fuera por construcción (F5).
ADVERB_HEADS = {"siempre", "always"}

# Ventana de adyacencia imperativo↔siempre (tokens), cerrada a propósito.
ADJACENCY_TOKENS = 3


def sb_get(**params) -> list[dict]:
    with httpx.Client(timeout=120.0) as client:
        resp = client.get(
            f"{SUPABASE_URL}/rest/v1/{TABLE}",
            headers={
                "apikey": SUPABASE_SERVICE_KEY,
                "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
            },
            params=params,
        )
        resp.raise_for_status()
        return resp.json()


def fetch_population(limit: int) -> list[dict]:
    """Población = TODO chunk del corpus con «siempre» o «always» (ES+EN)."""
    rows: dict[str, dict] = {}
    for needle in ("ilike.*siempre*", "ilike.*always*"):
        offset = 0
        while True:
            # `order=id` NO es cosmético: sin ORDER BY, Postgres no garantiza orden
            # estable entre páginas y la paginación duplica/saltea filas → la
            # población (y por tanto TODAS las cifras) sale distinta en cada corrida.
            # Cazado en s294: 268 vs 235 capturas con el mismo código.
            page = sb_get(
                select="id,source_file,page_number,chunk_index,product_model,language,content",
                content=needle,
                order="id",
                limit=str(min(1000, limit)),
                offset=str(offset),
            )
            for row in page:
                rows[row["id"]] = row
            if len(page) < min(1000, limit) or len(rows) >= limit:
                break
            offset += len(page)
    return list(rows.values())


def first_token(sentence: str) -> str:
    match = re.search(r"[A-Za-zÁÉÍÓÚÑáéíóúñÜü]+", sentence or "")
    return match.group(0).lower() if match else ""


def tokens_between(sentence: str, word_rx: re.Pattern) -> int | None:
    """Nº de tokens entre el primer verbo (token 0) y la palabra buscada."""
    match = word_rx.search(sentence)
    if not match:
        return None
    return len(re.findall(r"\S+", sentence[: match.start()])) - 1


# ── F3 · auditoría de integridad de span ─────────────────────────────────────────
def span_defects(sentence: str) -> list[str]:
    defects = []
    text = sentence.strip()
    if not text:
        return ["vacio"]
    if len(" ".join(text.split())) < 40:
        defects.append("bajo_min_clause_content")   # < _MIN_CLAUSE_CONTENT de producción
    if text.endswith((":", ";", ",", "cap.", "apartado", "seccion", "sección")):
        defects.append("decapitada")
    if re.search(r"\b(?:cap|apartado|secci[oó]n|fig|tabla)\.?\s*$", text, re.IGNORECASE):
        defects.append("referencia_truncada")
    if len(re.findall(r"[.!?]\s+[A-ZÁÉÍÓÚÑ]", text)) >= 2:
        defects.append("fusion_de_oraciones")
    if text.count("|") >= 2:
        defects.append("fila_de_tabla")
    if re.match(r"^[a-záéíóúñü]", text) and not re.match(r"^\W", text):
        defects.append("arranque_en_minuscula")
    if re.match(r"^#{1,6}\s", text):
        defects.append("cabecera")
    return defects


def scan(rows: list[dict], closed_es: tuple[str, ...], closed_en: tuple[str, ...]):
    captures, discovery, rejected = [], Counter(), []
    for row in rows:
        content = str(row.get("content") or "")
        for s_start, s_end in sentence_spans(content):
            sentence = content[s_start:s_end]
            pending_rejection = None
            has_es = bool(RX_SIEMPRE.search(sentence))
            has_en = bool(RX_ALWAYS.search(sentence))
            if not (has_es or has_en):
                continue
            if has_es and RX_COND_ES.search(sentence):
                continue                       # condicional: fuera por construcción
            head = first_token(sentence)
            lang = "es" if has_es else "en"
            gap = tokens_between(sentence, RX_SIEMPRE if has_es else RX_ALWAYS)

            # discovery: qué verbo abre las oraciones con «siempre» adyacente
            if gap is not None and 0 <= gap <= ADJACENCY_TOKENS:
                discovery[f"{lang}:{head}"] += 1

            form = None
            closed = closed_es if lang == "es" else closed_en
            if head in closed and gap is not None and 0 <= gap <= ADJACENCY_TOKENS:
                form = "A_imperativo_cerrado"          # verbo primero
            elif head in ADVERB_HEADS:
                # adverbio primero: el imperativo debe caer dentro de la ventana
                following = re.findall(r"[A-Za-zÁÉÍÓÚÑáéíóúñÜü]+", sentence)[1:1 + ADJACENCY_TOKENS]
                hit = next((w for w in following if w.lower() in closed), None)
                if hit:
                    form = "A_adverbio_primero"
                elif following:
                    # NO-CAP-SILENCIOSO: el hueco se registra, no se traga. Se anota
                    # como CANDIDATO y solo cuenta como rechazo si NINGUNA forma lo
                    # captura después (la v1 lo contaba antes de evaluar B y por eso
                    # inflaba el hueco con frases que B sí capturaba).
                    pending_rejection = {
                        "lang": lang, "head_siguiente": following[0].lower(),
                        "span": sentence.strip()[:180],
                    }
            if form is None and lang == "es" and RX_DEONTIC_ES.search(sentence):
                form = "B_deontico_reforzado"
            elif form is None and lang == "en" and RX_DEONTIC_EN.search(sentence):
                form = "B_deontico_reforzado"
            if not form:
                if pending_rejection is not None:
                    rejected.append(pending_rejection)
                continue
            captures.append({
                "chunk_id": row["id"],
                "source_file": row.get("source_file"),
                "page_number": row.get("page_number"),
                "product_model": row.get("product_model"),
                "language_meta": row.get("language"),
                "lang_detectado": lang,
                "form": form,
                "head_verb": head,
                "span": sentence.strip(),
                "span_defects": span_defects(sentence),
                "adjudicacion": None,          # F7: la rellena un adjudicador CIEGO
                "clase_espuria": None,
            })
    return captures, discovery, rejected


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    rows = fetch_population(LIMIT)
    sha = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True).stdout.decode().strip()

    if MODE == "discover":
        _caps, discovery, _rej = scan(rows, (), ())     # listas vacías: solo descubre
        top = discovery.most_common(120)
        out = {
            "probe": "s294_siempre_discovery_v1", "git_sha": sha,
            "poblacion_chunks": len(rows),
            "adjacency_tokens": ADJACENCY_TOKENS,
            "nota": "verbo que ABRE la oración cuando «siempre»/«always» aparece a "
                    "<=3 tokens; insumo para congelar la lista cerrada (F6)",
            "cabezas": [{"head": k, "n": v} for k, v in top],
        }
        path = os.path.join(os.getcwd(), "evals", "s294_siempre_discovery_v1.json")
    else:
        captures, _disc, rejected = scan(rows, CLOSED_IMPERATIVES_ES, CLOSED_IMPERATIVES_EN)
        by_form = Counter(c["form"] for c in captures)
        by_lang = Counter(c["lang_detectado"] for c in captures)
        with_defects = [c for c in captures if c["span_defects"]]
        out = {
            "probe": "s294_siempre_census_v1", "git_sha": sha,
            "poblacion_chunks": len(rows),
            "taxonomia_espurio_PRE_REGISTRADA": SPURIOUS_TAXONOMY,
            "regla_de_dano": "cualquier fila adjudicada ESPURIA ⇒ STOP del lever",
            "lista_cerrada_es": list(CLOSED_IMPERATIVES_ES),
            "lista_cerrada_en": list(CLOSED_IMPERATIVES_EN),
            "adjacency_tokens": ADJACENCY_TOKENS,
            "n_capturas": len(captures),
            "por_forma": dict(by_form),
            "por_idioma": dict(by_lang),
            "n_con_defecto_de_span": len(with_defects),
            "defectos": dict(Counter(d for c in captures for d in c["span_defects"])),
            "n_rechazadas_verbo_fuera_de_lista": len(rejected),
            "rechazadas_muestra": rejected[:25],
            "capturas": captures,
        }
        path = os.path.join(os.getcwd(), "evals", "s294_siempre_census_v1.json")

    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(f"escrito: {path}")
    print(json.dumps({k: v for k, v in out.items()
                      if k not in {"capturas", "cabezas", "taxonomia_espurio_PRE_REGISTRADA"}},
                     ensure_ascii=False)[:900])


if __name__ == "__main__":
    main()
