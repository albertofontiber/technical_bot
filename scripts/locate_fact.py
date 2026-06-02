#!/usr/bin/env python3
"""locate_fact.py — C4: localizador ROBUSTO de hechos para autoría de golds.

Diseño durable: docs/RULER_DESIGN.md §2 (decisión DEC-009). Implementa la
LOCALIZACIÓN EXHAUSTIVA (no budget-bounded) + confirmación por DOBLE-SEÑAL AND,
independiente del sustrato del bot.

Por qué no es circular (RULER_DESIGN §0): C4 grepea y renderiza los PDFs FUENTE
(la verdad), NO rankea chunks_v2/Voyage (= el sustrato que el bot usa). chunks_v2
se consulta SOLO para el check de existencia (flag GAP-DE-CORPUS), nunca para
decidir dónde está el dato.

Pipeline (RULER_DESIGN §2):
  1. producto→manuales: source_files del producto en chunks_v2 → resueltos a PDFs
     LOCALES (dedup por nombre; filtro ES/EN; las carpetas *_Privado se descartan).
  2. grep multi-manual EXHAUSTIVO: por-página, términos ES+EN + valores distintivos
     (los valores —números/códigos— son idioma-independientes y sobreviven al fraseo).
  3. render ±1 vecina de cada candidata (caza el off-by-one de hp005/17/18).
  4. DOBLE-SEÑAL AND:
       (a) lectura cross-model GPT-5.5 del RENDER (lee píxeles)  Y
       (b) match determinista (strict_match) del valor en el TEXTO EXTRAÍDO de esa
           página.
     En scan / texto corrupto la señal (b) FALLA aunque (a) acierte → `needs_human`
     (no fabricar). Discrepancia entre señales → `needs_human`.
  5. corpus-check: existencia del source_file (y página) en chunks_v2 → si está en el
     PDF pero NO en el corpus = GAP DE CORPUS (no fallo del bot; lever de extracción).
  6. emite por-candidata: veredicto + auditoría de localización (cobertura por-manual,
     digital/scan) en el shape de _provenance.localizacion de gold_store.

NO autora prosa ni decide conducta: SOLO localiza + confirma la ubicación de un hecho.
Su salida la consume author_atomic_facts / gold_store.upsert.

Uso CLI:
  # spec inline
  python scripts/locate_fact.py --product Pearl --manufacturer Notifier \\
      --terms "causa.?efecto,retardo,output delay" --values "512,240" --no-vlm
  # spec en JSON (para validación ciega contra golds existentes)
  python scripts/locate_fact.py --spec evals/_c4_spec_hp017.json
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path

import fitz  # PyMuPDF (ya en el stack de ingesta)
import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import (  # noqa: E402
    SUPABASE_URL, SUPABASE_SERVICE_KEY, CHUNKS_TABLE, OPENAI_API_KEY,
)
from scripts.strict_match import (  # noqa: E402
    norm_ocr, distinctive, chunk_has_quote_strict,
)

ROOT = Path(__file__).resolve().parent.parent
CROSS_MODEL = os.getenv("CROSS_VERIFY_MODEL", "gpt-5.5")
SERVED_LANGS = {"es", "en"}
# Carpetas duplicadas (copias privadas / multiling.) que NO deben contar dos veces
# ni desviar la resolución del PDF. La verdad de la localización es UNA copia.
_DUP_DIR_MARKERS = ("_Privado", "_privado")


# ───────────────────────── estructuras ─────────────────────────
@dataclass
class Manual:
    source_file: str          # nombre tal cual en chunks_v2 (sin .pdf)
    path: Path | None         # PDF local resuelto (None si no se encuentra)
    in_corpus: bool           # tiene chunks en chunks_v2
    n_pages: int = 0
    scan_ratio: float = 0.0   # fracción de páginas con texto casi-nulo (heurística scan)

    @property
    def is_scan(self) -> bool:
        # Regla de scans (RULER_DESIGN §2): grep casi-cero = INVÁLIDO como ausencia.
        return self.scan_ratio >= 0.6


@dataclass
class Confirmation:
    source_file: str
    page: int                 # 1-indexed (como cita el gold)
    grep_snippet: str
    strict_text_signal: bool  # (b) valor + contexto del predicado en el texto extraído
    context_term: str         # término de contexto hallado junto al valor ('' si ninguno)
    vlm_signal: bool          # (a) cross-model confirma el predicado leyendo el render
    vlm_raw: str
    render_png: str
    render_window: list[str]  # [p-1, p, p+1] renderizadas (RULER_DESIGN §2)
    in_corpus: bool
    verdict: str = "needs_human"  # confirmed | needs_human | corpus_gap


@dataclass
class LocationResult:
    product: str
    terms: list[str]
    values: list[str]
    manuals: list[dict] = field(default_factory=list)
    confirmations: list[dict] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


# ─────────────────── 1. producto → manuales locales ───────────────────
def _supa_get(params: dict, *, table: str | None = None, timeout: float = 20.0) -> list[dict]:
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    }
    with httpx.Client(timeout=timeout) as client:
        resp = client.get(
            f"{SUPABASE_URL}/rest/v1/{table or CHUNKS_TABLE}",
            headers=headers, params=params,
        )
        resp.raise_for_status()
    return resp.json()


# DEC-009 / revisión adversarial s39: el SET de manuales NO se deriva de
# `product_model` (estructuralmente sucio: doc-codes 'MPDT-280', 'AM2020 y AFP1010',
# familia dispersa en ≥5 etiquetas → eq/imatch pierde manuales del gold, p.ej. el lado
# US de hp012). Tampoco "carpeta del fabricante" (solo 2/23 fabricantes tienen carpeta).
# En su lugar (opción D): set EXPLÍCITO del autor (autoritativo) o SUGERENCIA exhaustiva
# dirigida por FILESYSTEM (la fuente de verdad, §0). chunks_v2 solo marca corpus-existence.
def _imatch_pattern(model: str) -> str:
    """Patrón PostgREST imatch (separadores opcionales + word-boundary) para un modelo."""
    parts = [p for p in re.split(r"[- ]+", model.strip()) if p]
    if not parts:
        return ""
    core = r"[- ]*".join(re.escape(p) for p in parts)
    return rf"\y{core}(?!\d)"


def _imatch_source_files(alias: str) -> set[str]:
    """source_files cuyo product_model imatchea el alias (HINT de chunks_v2, no autoridad)."""
    pat = _imatch_pattern(alias)
    if not pat:
        return set()
    try:
        rows = _supa_get({"product_model": f"imatch.{pat}", "select": "source_file", "limit": "20000"})
    except Exception:
        return set()
    return {r["source_file"] for r in rows if r.get("source_file")}


def _is_priv(path: Path) -> bool:
    return any(m in str(path) for m in _DUP_DIR_MARKERS)


def _lang_ok_filename(stem: str) -> bool:
    return not re.search(r"(?:_|-)(pt|port|fr|it|de)$", stem, re.IGNORECASE)


def _all_manual_pdfs() -> list[Path]:
    """Todos los PDFs bajo carpetas Manuales_* (la FUENTE de verdad, no chunks_v2)."""
    out: list[Path] = []
    for d in ROOT.glob("Manuales_*"):
        if d.is_dir():
            out += list(d.rglob("*.pdf")) + list(d.rglob("*.PDF"))
    return out


def suggest_manuals(product: str, manufacturer: str | None = None,
                    aliases: list[str] | None = None) -> dict[str, Path]:
    """Sugerencia EXHAUSTIVA producto→PDFs (stem→path, prefiere copia no-_Privado).

    Desacoplada de product_model. Une 3 señales sobre el FILESYSTEM + un hint:
      (a) filename: PDFs cuyo nombre contiene el modelo/alias (caza doc-codes que la
          metadata mis-etiqueta, p.ej. 'CAD-150' en '...CAD-150-8...');
      (b) carpeta dedicada del fabricante (Manuales_<Mfr>/ + _Privado) si existe;
      (c) hint chunks_v2 vía imatch, resuelto a PDF local.
    Es SUGERENCIA, no autoridad: los doc-code puros (MPDT280) NO salen de (a)/(c) →
    los aporta el autor con --manuals (sembrar exhaustivo y PODAR > añadir). Incluye
    _Privado (288 docs únicos en Notifier, donde viven manuales de gold)."""
    aliases = [product] + (aliases or [])
    norm_aliases = [re.sub(r"[- ]", "", a).lower() for a in aliases if a]
    stems: dict[str, Path] = {}

    def add(p: Path) -> None:
        if p.suffix.lower() != ".pdf" or not _lang_ok_filename(p.stem):
            return
        key = p.stem.lower()
        if key not in stems or (_is_priv(stems[key]) and not _is_priv(p)):
            stems[key] = p  # prefiere la copia no-_Privado

    pdfs = _all_manual_pdfs()
    for p in pdfs:  # (a) filename
        sn = re.sub(r"[- ]", "", p.stem).lower()
        if any(na and na in sn for na in norm_aliases):
            add(p)
    if manufacturer:  # (b) carpeta dedicada
        marker = f"manuales_{manufacturer}".lower()
        for p in pdfs:
            if marker in str(p).lower():
                add(p)
    sfs: set[str] = set()  # (c) hint chunks_v2
    for a in aliases:
        sfs |= _imatch_source_files(a)
    for sf in sfs:
        rp = _resolve_local_pdf(sf)
        if rp:
            add(rp)
    return stems


def _resolve_local_pdf(source_file: str) -> Path | None:
    """Resuelve un source_file a su PDF local, deduplicando copias *_Privado.

    chunks_v2 guarda el source_file sin extensión; los PDFs viven en Manuales_*/.
    rglob por nombre devuelve multi-match (carpetas duplicadas) → preferimos la copia
    NO-privada y nos quedamos con una sola.
    """
    stem = source_file[:-4] if source_file.lower().endswith(".pdf") else source_file
    matches = [p for p in ROOT.rglob(f"{stem}.pdf")] + [p for p in ROOT.rglob(f"{stem}.PDF")]
    if not matches:
        return None
    non_priv = [p for p in matches if not any(m in str(p) for m in _DUP_DIR_MARKERS)]
    pool = non_priv or matches
    return sorted(pool, key=lambda p: len(str(p)))[0]


def _scan_ratio(path: Path) -> tuple[int, float]:
    """(n_pages, fracción de páginas con texto casi-nulo). Heurística de scan."""
    doc = fitz.open(path)
    n = doc.page_count
    empty = 0
    for i in range(n):
        if len(doc.load_page(i).get_text().strip()) < 20:
            empty += 1
    doc.close()
    return n, (empty / n if n else 0.0)


def producto_a_manuales(product: str, manufacturer: str | None = None,
                        manuals: list[str] | None = None) -> list[Manual]:
    """Resuelve el SET de manuales a grepear.
      - `manuals` (lista explícita del autor) → AUTORITATIVO (cada uno resuelto, incl.
        copias _Privado; sin filtro de idioma — el autor manda).
      - si no → `suggest_manuals` (exhaustivo, filesystem-driven).
    `in_corpus` se consulta a chunks_v2 SOLO como flag (corpus-gap), nunca decide el set."""
    if manuals:
        pairs = [((m[:-4] if m.lower().endswith(".pdf") else m), _resolve_local_pdf(m))
                 for m in manuals]
    else:
        pairs = [(p.stem, p) for p in suggest_manuals(product, manufacturer).values()]
    seen: set[str] = set()
    out: list[Manual] = []
    for stem, path in sorted(pairs, key=lambda x: x[0].lower()):
        if stem.lower() in seen:
            continue
        seen.add(stem.lower())
        n_pages, scan = _scan_ratio(path) if path else (0, 0.0)
        out.append(Manual(source_file=stem, path=path, in_corpus=corpus_has(stem),
                          n_pages=n_pages, scan_ratio=scan))
    return out


# ─────────────────── 2. grep multi-manual ───────────────────
def grep_pdf(path: Path, patterns: list[re.Pattern], ctx: int = 140) -> list[tuple[int, str, str]]:
    """Devuelve (page_1indexed, snippet, patrón) por cada coincidencia."""
    out: list[tuple[int, str, str]] = []
    doc = fitz.open(path)
    for i in range(doc.page_count):
        txt = doc.load_page(i).get_text()
        ntxt = norm_ocr(txt)
        for rx in patterns:
            m = rx.search(ntxt)
            if m:
                s = max(0, m.start() - ctx)
                e = min(len(ntxt), m.end() + ctx)
                out.append((i + 1, " ".join(ntxt[s:e].split()), rx.pattern))
                break  # 1 hit por página basta para marcarla candidata
    doc.close()
    return out


def _build_patterns(terms: list[str], values: list[str]) -> list[re.Pattern]:
    pats: list[re.Pattern] = []
    for t in terms:
        try:
            pats.append(re.compile(t, re.IGNORECASE))
        except re.error:
            pats.append(re.compile(re.escape(t), re.IGNORECASE))
    # los valores distintivos (idioma-independientes) se grepean literales, OCR-normalizados
    for v in values:
        pats.append(re.compile(re.escape(norm_ocr(v))))
    return pats


def page_text(path: Path, page_1indexed: int) -> str:
    doc = fitz.open(path)
    if not (1 <= page_1indexed <= doc.page_count):
        doc.close()
        return ""
    txt = doc.load_page(page_1indexed - 1).get_text()
    doc.close()
    return txt


def _value_on_page(text: str, value: str) -> bool:
    """¿Está el valor del hecho en la página? Más estricto que el matcher de prosa
    canónico A PROPÓSITO (RULER_DESIGN §2: predicado completo, no tokens dispersos):
      - valor con ancla numérica/código → TODOS los anchors presentes (caso fuerte);
      - valor de prosa/frase → SUBSTRING CONTIGUO normalizado (no token-overlap, que
        explotaba a 21 candidatas en hp005: 'coincidencia'+'2'+'equipos' dispersos).
    No modifica strict_match.py (matcher compartido por atomic_scorer); endurece local.
    """
    nt = norm_ocr(text)
    anchors = distinctive(value)
    if anchors:
        # Frontera de dígito (revisión adversarial s39): substring crudo daba
        # "792"∈"13792" y "512"∈"1512" (la clase de FP que el ancla debe evitar).
        return all(re.search(rf"(?<![\d.,]){re.escape(a)}(?![\d.,])", nt) for a in anchors)
    return norm_ocr(value) in nt


def value_pages(path: Path, values: list[str]) -> list[int]:
    """Páginas (1-indexed) donde aparecen TODOS los valores distintivos del hecho.

    El valor es el ANCLA: el número/código (o la frase literal) del hecho TIENE que
    estar en la página. Páginas con los términos pero sin el valor son ruido.
    """
    if not values:
        return []
    doc = fitz.open(path)
    pages: list[int] = []
    for i in range(doc.page_count):
        txt = doc.load_page(i).get_text()
        if all(_value_on_page(txt, v) for v in values):
            pages.append(i + 1)
    doc.close()
    return pages


def context_on_page(text: str, context_terms: list[str]) -> str | None:
    """Devuelve el 1er término de contexto presente en la página, o None.

    Confirma el PREDICADO (RULER_DESIGN §2): el valor debe estar JUNTO a su
    parámetro ("512" + "regla"), no suelto ("512 sensores" ≠ "512 reglas").
    """
    n = norm_ocr(text)
    for t in context_terms:
        try:
            if re.search(t, n, re.IGNORECASE):
                return t
        except re.error:
            if norm_ocr(t) in n:
                return t
    return None


# ─────────────────── 3. render ±1 ───────────────────
def render_page(path: Path, page_1indexed: int, *, dpi: int = 200,
                out_dir: Path | None = None) -> Path | None:
    doc = fitz.open(path)
    if not (1 <= page_1indexed <= doc.page_count):
        doc.close()
        return None
    out_dir = out_dir or (ROOT / "logs" / "c4_render")
    out_dir.mkdir(parents=True, exist_ok=True)
    pix = doc.load_page(page_1indexed - 1).get_pixmap(dpi=dpi)
    dst = out_dir / f"{path.stem[:50]}_p{page_1indexed}_{dpi}dpi.png"
    pix.save(dst)
    doc.close()
    return dst


def render_window(path: Path, page_1indexed: int, *, dpi: int = 200) -> tuple[Path | None, list[str]]:
    """Render de la página ±1 vecina (RULER_DESIGN §2: caza off-by-one / tabla a
    caballo entre páginas). Devuelve (png_de_la_página, [todas las png del window])."""
    primary = render_page(path, page_1indexed, dpi=dpi)
    window: list[str] = []
    for p in (page_1indexed - 1, page_1indexed, page_1indexed + 1):
        png = render_page(path, p, dpi=dpi)
        if png:
            window.append(str(png.relative_to(ROOT)))
    return primary, window


# ─────────────────── 4. doble-señal AND ───────────────────
def vlm_read(png: Path, question: str) -> str:
    """(a) GPT-5.5 lee el render en frío (sin darle nuestra respuesta)."""
    from openai import OpenAI
    b64 = base64.b64encode(png.read_bytes()).decode()
    client = OpenAI(api_key=OPENAI_API_KEY)
    resp = client.chat.completions.create(
        model=CROSS_MODEL,
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": question},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
            ],
        }],
    )
    return resp.choices[0].message.content or ""


# El VLM puede transcribir el valor en un contexto AJENO al predicado ("512 salidas
# virtuales" cuando se pregunta por "512 reglas") y decir explícitamente que el
# predicado NO aparece. El booleano debe capturar su VEREDICTO, no solo si el token
# del valor cae en su texto (mismo fallo value-only que en la señal determinista).
_VLM_NEG = re.compile(
    r"\b(no aparece|no figura|no se (?:menciona|indica|encuentra|ve)|no est[áa]|"
    r"ausente|no contiene|not present|does not|doesn't|no:)", re.IGNORECASE)


def vlm_signal(png: Path, values: list[str], predicate: str) -> tuple[bool, str]:
    q = (
        "Eres un verificador independiente de un manual técnico. Lee SOLO esta página "
        f"renderizada. ¿Aparece EN ELLA el dato: «{predicate}»?\n"
        "- Si SÍ: responde 'SÍ:' y transcribe literalmente el valor con su parámetro "
        "(número/código/unidad exactos, como se ven).\n"
        "- Si NO aparece (aunque haya números parecidos en OTRO contexto): responde 'NO'.\n"
        "No infieras ni completes."
    )
    raw = vlm_read(png, q)
    val_ok = bool(values) and all(chunk_has_quote_strict(raw, v) for v in values)
    negated = bool(_VLM_NEG.search(raw))
    return (val_ok and not negated), raw


# ─────────────────── 5. corpus-check ───────────────────
def corpus_has(source_file: str, page: int | None = None) -> bool:
    stem = source_file[:-4] if source_file.lower().endswith(".pdf") else source_file
    params = {"source_file": f"eq.{stem}", "select": "id", "limit": "1"}
    if page is not None:
        params["page_number"] = f"eq.{page}"
    try:
        return len(_supa_get(params, timeout=10.0)) > 0
    except Exception:
        return False


# ─────────────────── orquestación ───────────────────
def _snippet(text: str, values: list[str], width: int = 160) -> str:
    n = norm_ocr(text)
    anchor = -1
    for v in values:
        i = n.find(norm_ocr(v))
        if i >= 0:
            anchor = i
            break
    if anchor < 0:
        return " ".join(n[:2 * width].split())
    return " ".join(n[max(0, anchor - width):anchor + width].split())


def locate_fact(product: str, terms: list[str], values: list[str], *,
                manufacturer: str | None = None, predicate: str = "",
                context: list[str] | None = None, manual_set: list[str] | None = None,
                use_vlm: bool = True, dpi: int = 200) -> LocationResult:
    res = LocationResult(product=product, terms=terms, values=values)
    context_terms = context or terms  # términos que deben CO-OCURRIR con el valor
    predicate = predicate or (", ".join(terms) + " | " + ", ".join(values))

    # SET de manuales: explícito del autor (autoritativo) o sugeridor exhaustivo (D).
    manuals = producto_a_manuales(product, manufacturer, manuals=manual_set)
    if not manuals:
        hint = (f"--manuals no resolvió ningún PDF local: {manual_set}" if manual_set else
                f"el sugeridor no halló PDFs para {product!r} (prueba --manuals explícito "
                f"o --manufacturer con carpeta dedicada).")
        res.notes.append(f"SIN manuales para grepear. {hint}")
        return res
    for mn in manuals:
        res.manuals.append({
            "source_file": mn.source_file,
            "local_pdf": str(mn.path.relative_to(ROOT)) if mn.path else None,
            "n_pages": mn.n_pages, "scan_ratio": round(mn.scan_ratio, 2),
            "is_scan": mn.is_scan, "in_corpus": mn.in_corpus,
        })
        if mn.path is None:
            res.notes.append(f"[{mn.source_file}] en corpus pero SIN PDF local → no verificable.")

    for mn in manuals:
        if mn.path is None:
            continue
        # Candidata = página donde aparece el VALOR (ancla). Página con términos pero
        # sin valor = ruido (no contiene el dato).
        vpages = value_pages(mn.path, values)
        if not vpages:
            term_hits = grep_pdf(mn.path, _build_patterns(context_terms, []))
            if term_hits:
                pp = sorted({p for p, _, _ in term_hits})[:8]
                res.notes.append(f"[{mn.source_file}] términos presentes pero el VALOR no es "
                                 f"extraíble del texto (¿tabla/scan? pp {pp}) → needs_human por "
                                 f"render/VLM; NO fabricar desde grep.")
            elif mn.is_scan:
                res.notes.append(f"[{mn.source_file}] doc-scan + grep≈0 → INVÁLIDO como ausencia "
                                 f"(regla de scans); needs_human si el dato debería estar aquí.")
            continue
        for p in vpages:
            txt = page_text(mn.path, p)
            ctx = context_on_page(txt, context_terms)  # (b): valor (ya presente) + contexto
            text_ok = ctx is not None
            primary, window = render_window(mn.path, p, dpi=dpi)
            # El VLM solo adjudica páginas que pasaron el gate determinista de contexto:
            # si text_ok=False el AND ya falla (needs_human) → no gastar la llamada.
            vlm_ok, vlm_raw = (False, "(VLM desactivado)" if not use_vlm else "(omitido: sin contexto)")
            if use_vlm and primary is not None and text_ok:
                vlm_ok, vlm_raw = vlm_signal(primary, values, predicate)
            in_corpus_pg = corpus_has(mn.source_file, p)
            if not in_corpus_pg and corpus_has(mn.source_file):
                verdict = "corpus_gap"
            elif text_ok and vlm_ok:
                verdict = "confirmed"
            elif text_ok and not use_vlm:
                verdict = "confirmed_text_only"
            else:
                verdict = "needs_human"  # falla contexto (valor fuera de predicado) o VLM discrepa
            res.confirmations.append(asdict(Confirmation(
                source_file=mn.source_file, page=p, grep_snippet=_snippet(txt, values),
                strict_text_signal=text_ok, context_term=ctx or "",
                vlm_signal=vlm_ok, vlm_raw=vlm_raw[:600],
                render_png=str(primary.relative_to(ROOT)) if primary else "",
                render_window=window, in_corpus=in_corpus_pg, verdict=verdict,
            )))
    if not res.confirmations and not res.notes:
        res.notes.append("El VALOR del hecho no aparece en ningún manual del producto "
                         "(¿valor mal formado, o dato ausente del corpus = posible admit/gap?).")
    return res


# ─────────────────── CLI ───────────────────
def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--spec", help="JSON con {product, manufacturer, manuals[], terms[], values[], context[], predicate}")
    ap.add_argument("--product")
    ap.add_argument("--manufacturer")
    ap.add_argument("--manuals", help="lista de source_files/stems EXPLÍCITA (autoritativa; "
                    "el autor la fija/poda). Si se omite, C4 sugiere candidatos (filesystem).")
    ap.add_argument("--terms", help="lista separada por comas (regex permitido; descubre candidatas)")
    ap.add_argument("--values", help="valores distintivos = ANCLA (conjuntivos: TODOS en la misma "
                    "página = UN hecho. Para un CONFLICTO ES-US corre C4 una vez POR LADO).")
    ap.add_argument("--context", help="términos que deben CO-OCURRIR con el valor "
                    "(predicado; default = --terms)")
    ap.add_argument("--predicate", default="")
    ap.add_argument("--no-vlm", action="store_true", help="dry-run sin cross-model (barato)")
    ap.add_argument("--dpi", type=int, default=200)
    ap.add_argument("--out", help="escribe el resultado JSON aquí")
    args = ap.parse_args()

    if args.spec:
        spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    else:
        if not (args.product and (args.terms or args.values)):
            ap.error("usa --spec o (--product + --terms/--values)")
        spec = {
            "product": args.product, "manufacturer": args.manufacturer,
            "manuals": [m.strip() for m in (args.manuals or "").split(",") if m.strip()],
            "terms": [t.strip() for t in (args.terms or "").split(",") if t.strip()],
            "values": [v.strip() for v in (args.values or "").split(",") if v.strip()],
            "context": [c.strip() for c in (args.context or "").split(",") if c.strip()],
            "predicate": args.predicate,
        }

    res = locate_fact(
        spec["product"], spec.get("terms", []), spec.get("values", []),
        manufacturer=spec.get("manufacturer"), predicate=spec.get("predicate", ""),
        context=spec.get("context") or None, manual_set=spec.get("manuals") or None,
        use_vlm=not args.no_vlm, dpi=args.dpi,
    )
    out = json.dumps(asdict(res), ensure_ascii=False, indent=2)
    print(out)
    if args.out:
        Path(args.out).write_text(out, encoding="utf-8")
        print(f"\n→ {args.out}", file=sys.stderr)
    n_conf = sum(1 for c in res.confirmations if c["verdict"].startswith("confirmed"))
    n_nh = sum(1 for c in res.confirmations if c["verdict"] == "needs_human")
    n_gap = sum(1 for c in res.confirmations if c["verdict"] == "corpus_gap")
    print(f"\n{len(res.manuals)} manual(es), {len(res.confirmations)} candidata(s): "
          f"{n_conf} confirmada(s) / {n_nh} needs_human / {n_gap} corpus_gap.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
