#!/usr/bin/env python3
"""catalog_store.py — ÚNICA puerta para leer/escribir el catálogo canónico de identidad.

Materializa el contrato `docs/IDENTITY_CATALOG_CONTRACT.md` (F0 aprobado por Alberto, DEC-079):
almacenamiento + VALIDACIÓN + resolución query-side. Patrón `gold_store` (la puerta valida;
ningún fichero del catálogo se edita a mano sin pasar por aquí / CI).

Fuente REPO-FIRST (D1): `data/catalog/*.jsonl`, un objeto por línea:
  products.jsonl   {id, canonical_model, vendido_bajo[], oem_manufacturer_marca?, familia?,
                    estado: activo|retirado|redirect, redirect_to?, candidate?, provenance, added_by}
  aliases.jsonl    {alias, id, tipo, provenance, added_by}
  umbrellas.jsonl  {termino, ids[], tipo: familia|serie|rango, divergent: true|false|unknown,
                    candidate, provenance, added_by}
  homonyms.jsonl   {termino, ids[], politica: clarify|prefer:<id>|fail-open, candidate,
                    provenance, added_by}
  relations.jsonl  {origen, destino, tipo: variant-of|rebrand-of|shared-doc|supersedes, provenance}
  doc_map.jsonl    {document_id, source_file, entries: [{id, role: primary|secondary,
                    scope: doc|paginas, paginas?[], provenance}]}
  docrel.jsonl     {doc_a, doc_b, tipo: language-variant-of|revision-of, provenance}

Reglas duras del contrato que ESTA puerta hace cumplir:
- id con NAMESPACE de marca (`marca:slug`), ÚNICO, INMUTABLE (merge/split = redirect, nunca borrado).
- alias/paraguas/homónimo → ids EXISTENTES; redirects ACÍCLICOS y a ids existentes.
- paraguas y homónimos NACEN candidate=true (blast-radius) hasta QA humano.
- resolve(): check-HOMÓNIMO PRIMERO → exact(canonical) → alias → paraguas; candidate NO se
  consume; fail-open (None) si no resuelve. Un token homónimo NUNCA cae a exact.

Uso CLI:
  python scripts/catalog_store.py validate    # chequeo de esquema/refs (lo corre CI)
  python scripts/catalog_store.py resolve <token> [...]
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG_DIR = ROOT / "data" / "catalog"

FILES = {
    "products": "products.jsonl", "aliases": "aliases.jsonl", "umbrellas": "umbrellas.jsonl",
    "homonyms": "homonyms.jsonl", "relations": "relations.jsonl", "doc_map": "doc_map.jsonl",
    "docrel": "docrel.jsonl",
}
ID_RX = re.compile(r"^[a-z0-9][a-z0-9_-]*:[a-z0-9][a-z0-9._+-]*$")   # marca:slug
ESTADOS = {"activo", "retirado", "redirect"}
TIPOS_ALIAS = {"variante-tipografica", "codigo-comercial", "nombre-largo", "numero-de-parte"}
TIPOS_UMBRELLA = {"familia", "serie", "rango"}
DIVERGENT = {True, False, "unknown"}
TIPOS_REL = {"variant-of", "rebrand-of", "shared-doc", "supersedes"}
TIPOS_DOCREL = {"language-variant-of", "revision-of"}
ROLES = {"primary", "secondary"}
SCOPES = {"doc", "paginas"}


def norm_token(s: str) -> str:
    """Normalización de matching (NO de almacenamiento): casefold + sin acentos + sin
    separadores. 'ZX-2e' == 'zx2e' == 'ZX 2E'. Los valores almacenados conservan su forma."""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return re.sub(r"[\s\-_/.]+", "", s.casefold().strip())


@dataclass
class Catalog:
    products: dict[str, dict] = field(default_factory=dict)      # id -> row
    aliases: list[dict] = field(default_factory=list)
    umbrellas: list[dict] = field(default_factory=list)
    homonyms: list[dict] = field(default_factory=list)
    relations: list[dict] = field(default_factory=list)
    doc_map: list[dict] = field(default_factory=list)
    docrel: list[dict] = field(default_factory=list)

    # índices de matching (norm_token -> ...) construidos en load()
    _by_canonical: dict[str, str] = field(default_factory=dict)
    _by_alias: dict[str, str] = field(default_factory=dict)
    _by_umbrella: dict[str, dict] = field(default_factory=dict)
    _by_homonym: dict[str, dict] = field(default_factory=dict)

    def _consumable(self, pid: str) -> bool:
        """Un id es consumible si su producto (tras redirects) está activo y NO-candidate.
        Fix dúo s90: 'candidate NO se consume' aplica al DESTINO, no solo al row que apunta."""
        p = self.products.get(self.follow_redirect(pid))
        return bool(p) and p.get("estado") == "activo" and not p.get("candidate")

    def build_indexes(self) -> None:
        self._by_canonical = {}
        for pid, p in self.products.items():
            if p.get("estado") == "activo" and not p.get("candidate"):
                self._by_canonical[norm_token(p["canonical_model"])] = pid
        # alias: ni el ROW candidate ni un DESTINO candidate/retirado se consumen
        self._by_alias = {norm_token(a["alias"]): a["id"] for a in self.aliases
                          if not a.get("candidate") and self._consumable(a["id"])}
        self._by_umbrella = {norm_token(u["termino"]): u for u in self.umbrellas
                             if not u.get("candidate")}
        self._by_homonym = {norm_token(h["termino"]): h for h in self.homonyms}
        # NOTA: los homónimos se indexan AUNQUE sean candidate — un homónimo candidate
        # BLOQUEA el exact-match del token (mejor fail-open que resolver mal un homónimo),
        # pero no aplica su política hasta QA.

    def follow_redirect(self, pid: str, _seen: frozenset = frozenset()) -> str:
        p = self.products.get(pid)
        if p and p.get("estado") == "redirect" and p.get("redirect_to"):
            if pid in _seen:      # ciclo — validate lo caza; aquí fail-safe
                return pid
            return self.follow_redirect(p["redirect_to"], _seen | {pid})
        return pid

    def resolve(self, token: str) -> dict | None:
        """Resolución query-side del contrato (§5.1): check-homónimo PRIMERO → exact →
        alias → paraguas. Devuelve None (fail-open) o un dict con:
          ids     — los id_canonico implicados
          via     — exact|alias|paraguas|homonimo|homonimo-candidate|paraguas-unknown
          expand  — CONTRATO PARA EL CONSUMIDOR (dúo s90): True = usar los ids para
                    retrieval; False = NO expandir (los ids son solo las OPCIONES de un
                    clarify o información de diagnóstico). Un consumidor que ignore
                    `expand` y expanda un clarify contaminaría el pool.
          all_members_consumable — s278 §1a (GUARD-IMPL): True solo si la expansión NO
                    filtró ningún miembro (paraguas: TODOS los u.ids consumibles; alias/
                    homónimo-prefer: el id expuesto ya pasó _consumable — los demás ids de
                    un homónimo prefer NO son miembros de la expansión, la política elige
                    uno). Un consumidor `replace` NO debe dropear un token con False: la
                    expansión está incompleta (clase FAAST: miembro candidate filtrado en
                    silencio) y el drop perdería alcance. La vía exact NO lleva el campo
                    (un solo id consumible por construcción, nunca drop-elegible; su shape
                    está pineado en test_catalog_store.py::test_resolve_exact).
        candidate NO se consume (salvo el BLOQUEO de homónimo); divergent=='unknown'
        en paraguas → fail-open SIN expansión (la letra del contrato §5.1)."""
        t = norm_token(token)
        if not t:
            return None
        h = self._by_homonym.get(t)
        if h is not None:
            if h.get("candidate"):
                return {"ids": [], "via": "homonimo-candidate", "politica": "fail-open",
                        "expand": False, "all_members_consumable": False}
            pol = h.get("politica", "fail-open")
            if pol.startswith("prefer:"):
                pid = pol.split(":", 1)[1]
                if not self._consumable(pid):   # prefer a candidate/retirado → fail-open
                    return {"ids": [], "via": "homonimo", "politica": pol, "expand": False,
                            "all_members_consumable": False}
                # la expansión del prefer = SOLO el id preferido (adjudicado) y ya pasó
                # _consumable — el guard no debe bloquear el drop de un prefer sano
                return {"ids": [self.follow_redirect(pid)], "via": "homonimo",
                        "politica": pol, "expand": True, "all_members_consumable": True}
            # clarify/fail-open: los ids son OPCIONES (productos DISTINTOS sin familia) —
            # expandirlos al retrieval contaminaría el pool.
            return {"ids": [self.follow_redirect(i) for i in h["ids"]],
                    "via": "homonimo", "politica": pol, "expand": False,
                    "all_members_consumable": all(self._consumable(i) for i in h["ids"])}
        pid = self._by_canonical.get(t)
        if pid:
            return {"ids": [self.follow_redirect(pid)], "via": "exact", "expand": True}
        pid = self._by_alias.get(t)
        if pid:
            return {"ids": [self.follow_redirect(pid)], "via": "alias", "expand": True,
                    "all_members_consumable": True}
        u = self._by_umbrella.get(t)
        if u is not None:
            div = u.get("divergent", "unknown")
            # GUARD-IMPL s278: el filtrado de abajo es SILENCIOSO — se declara aquí para
            # que el consumidor replace sepa si la expansión está completa antes de dropear
            amc = all(self._consumable(i) for i in u["ids"])
            if div == "unknown":
                # contrato §5.1: unknown → fail-open (SIN expansión) hasta adjudicar
                return {"ids": [], "via": "paraguas-unknown", "divergent": "unknown",
                        "expand": False, "all_members_consumable": amc}
            # divergent True/False: el RETRIEVAL expande igual (recuperar los docs de las
            # variantes = el fix hp018); la conducta clarify-vs-answer es del consumidor F2.
            # Los miembros candidate/retirados se FILTRAN (no se consumen — fix dúo s90).
            ids = [self.follow_redirect(i) for i in u["ids"] if self._consumable(i)]
            if not ids:
                return {"ids": [], "via": "paraguas", "divergent": div, "expand": False,
                        "all_members_consumable": amc}
            return {"ids": ids, "via": "paraguas", "divergent": div, "expand": True,
                    "all_members_consumable": amc}
        return None   # fail-open


# ─────────────────────────────── load / validate ───────────────────────────────
def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as e:
            raise ValueError(f"{path.name}:{n}: JSON inválido: {e}") from e
    return rows


def load(catalog_dir: Path = CATALOG_DIR) -> Catalog:
    cat = Catalog()
    prows = _read_jsonl(catalog_dir / FILES["products"])
    cat.products = {r["id"]: r for r in prows}
    if len(cat.products) != len(prows):
        raise ValueError("products.jsonl: ids duplicados (validate da el detalle)")
    cat.aliases = _read_jsonl(catalog_dir / FILES["aliases"])
    cat.umbrellas = _read_jsonl(catalog_dir / FILES["umbrellas"])
    cat.homonyms = _read_jsonl(catalog_dir / FILES["homonyms"])
    cat.relations = _read_jsonl(catalog_dir / FILES["relations"])
    cat.doc_map = _read_jsonl(catalog_dir / FILES["doc_map"])
    cat.docrel = _read_jsonl(catalog_dir / FILES["docrel"])
    cat.build_indexes()
    return cat


def validate(catalog_dir: Path = CATALOG_DIR) -> list[str]:
    """Devuelve la lista de errores (vacía = OK). Reglas duras del contrato."""
    errors: list[str] = []
    try:
        prows = _read_jsonl(catalog_dir / FILES["products"])
    except ValueError as e:
        return [str(e)]
    seen_ids: set[str] = set()
    for r in prows:
        pid = r.get("id", "")
        if not ID_RX.match(pid):
            errors.append(f"products: id sin namespace marca:slug válido: {pid!r}")
        if pid in seen_ids:
            errors.append(f"products: id DUPLICADO: {pid!r}")
        seen_ids.add(pid)
        if r.get("estado") not in ESTADOS:
            errors.append(f"products[{pid}]: estado inválido {r.get('estado')!r}")
        if r.get("estado") == "redirect" and not r.get("redirect_to"):
            errors.append(f"products[{pid}]: redirect sin redirect_to")
        if r.get("estado") != "redirect" and r.get("redirect_to"):
            errors.append(f"products[{pid}]: redirect_to en estado {r.get('estado')!r}")
        if not r.get("canonical_model"):
            errors.append(f"products[{pid}]: canonical_model vacío")
        if not isinstance(r.get("vendido_bajo"), list) or not r.get("vendido_bajo"):
            errors.append(f"products[{pid}]: vendido_bajo debe ser lista no-vacía")
        if not r.get("provenance") or not r.get("added_by"):
            errors.append(f"products[{pid}]: provenance/added_by obligatorios (anti-Excel-opaco)")
    # redirects: destino existe + acíclico
    by_id = {r["id"]: r for r in prows}
    for r in prows:
        if r.get("estado") == "redirect":
            seen, cur = {r["id"]}, r.get("redirect_to")
            while cur:
                if cur not in by_id:
                    errors.append(f"products[{r['id']}]: redirect_to inexistente {cur!r}")
                    break
                if cur in seen:
                    errors.append(f"products[{r['id']}]: CICLO de redirects vía {cur!r}")
                    break
                seen.add(cur)
                nxt = by_id[cur]
                cur = nxt.get("redirect_to") if nxt.get("estado") == "redirect" else None

    def _check_ref(kind: str, key: str, pid: str) -> None:
        if pid not in seen_ids:
            errors.append(f"{kind}[{key}]: referencia a id inexistente {pid!r}")

    def _check_prov(kind: str, key: str, row: dict, added_by: bool = True) -> None:
        # anti-Excel-opaco en TODAS las colecciones, no solo products (fix dúo s90)
        if not row.get("provenance") or (added_by and not row.get("added_by")):
            errors.append(f"{kind}[{key}]: provenance/added_by obligatorios (anti-Excel-opaco)")

    # canonicals CONSUMIBLES (activo + no-candidate = los que entran a _by_canonical) — la
    # colisión solo es ambigüedad real entre consumibles; los candidate no se indexan (s91).
    canon_norm: dict[str, str] = {}
    for r in prows:
        if r.get("estado") == "activo" and r.get("canonical_model") and not r.get("candidate"):
            k = norm_token(r["canonical_model"])
            if k in canon_norm:
                errors.append(f"products: canonical_model DUPLICADO tras normalizar "
                              f"({canon_norm[k]!r} vs {r['id']!r}) — exact sería last-wins silencioso; adjudicar (¿merge?)")
            canon_norm[k] = r["id"]
    seen_alias: set[str] = set()
    for a in _read_jsonl(catalog_dir / FILES["aliases"]):
        k = norm_token(a.get("alias", ""))
        if not k:
            errors.append(f"aliases: alias vacío ({a})")
            continue
        if k in seen_alias:
            errors.append(f"aliases: alias duplicado (tras normalizar): {a.get('alias')!r}")
        seen_alias.add(k)
        # colisión alias↔canonical de OTRO producto: exact ganaría al alias en resolve()
        # → ambigüedad silenciosa (la clase ZXr-A cazada por el smoke F1a)
        owner = canon_norm.get(k)
        if owner and owner != a.get("id"):
            errors.append(f"aliases[{a.get('alias')}]: COLISIONA con canonical_model de {owner!r} "
                          f"(apunta a {a.get('id')!r}) — exact pisaría el alias; adjudicar (¿merge?)")
        if a.get("tipo") not in TIPOS_ALIAS:
            errors.append(f"aliases[{a.get('alias')}]: tipo inválido {a.get('tipo')!r}")
        _check_ref("aliases", a.get("alias", "?"), a.get("id", ""))
        _check_prov("aliases", a.get("alias", "?"), a)
    seen_terms: set[str] = set()
    for u in _read_jsonl(catalog_dir / FILES["umbrellas"]):
        tk = norm_token(u.get("termino", ""))
        if tk in seen_terms:
            errors.append(f"umbrellas: término DUPLICADO tras normalizar: {u.get('termino')!r}")
        seen_terms.add(tk)
        _check_prov("umbrellas", u.get("termino", "?"), u)
        if u.get("tipo") not in TIPOS_UMBRELLA:
            errors.append(f"umbrellas[{u.get('termino')}]: tipo inválido {u.get('tipo')!r}")
        if u.get("divergent") not in DIVERGENT:
            errors.append(f"umbrellas[{u.get('termino')}]: divergent inválido {u.get('divergent')!r}")
        if "candidate" not in u:
            errors.append(f"umbrellas[{u.get('termino')}]: candidate obligatorio (nacen candidate)")
        if len(u.get("ids") or []) < 1:
            errors.append(f"umbrellas[{u.get('termino')}]: ids vacío")
        for pid in u.get("ids") or []:
            _check_ref("umbrellas", u.get("termino", "?"), pid)
    seen_hterms: set[str] = set()
    for h in _read_jsonl(catalog_dir / FILES["homonyms"]):
        tk = norm_token(h.get("termino", ""))
        if tk in seen_hterms:
            errors.append(f"homonyms: término DUPLICADO tras normalizar: {h.get('termino')!r}")
        seen_hterms.add(tk)
        _check_prov("homonyms", h.get("termino", "?"), h)
        ids = h.get("ids") or []
        if len(ids) < 2:
            errors.append(f"homonyms[{h.get('termino')}]: un homónimo exige ≥2 ids (si no, es alias)")
        pol = h.get("politica", "")
        if not (pol in ("clarify", "fail-open") or pol.startswith("prefer:")):
            errors.append(f"homonyms[{h.get('termino')}]: politica inválida {pol!r}")
        if pol.startswith("prefer:") and pol.split(":", 1)[1] not in seen_ids:
            errors.append(f"homonyms[{h.get('termino')}]: prefer a id inexistente")
        if "candidate" not in h:
            errors.append(f"homonyms[{h.get('termino')}]: candidate obligatorio (nacen candidate)")
        for pid in ids:
            _check_ref("homonyms", h.get("termino", "?"), pid)
    for rel in _read_jsonl(catalog_dir / FILES["relations"]):
        _check_prov("relations", f"{rel.get('origen')}→{rel.get('destino')}", rel, added_by=False)
        if rel.get("tipo") not in TIPOS_REL:
            errors.append(f"relations: tipo inválido {rel.get('tipo')!r}")
        for k in ("origen", "destino"):
            _check_ref("relations", f"{rel.get('origen')}→{rel.get('destino')}", rel.get(k, ""))
    seen_docids: set[str] = set()
    for dm in _read_jsonl(catalog_dir / FILES["doc_map"]):
        if not dm.get("document_id"):
            errors.append(f"doc_map: document_id obligatorio (clave estable, no source_file): {dm.get('source_file')}")
        elif dm["document_id"] in seen_docids:
            errors.append(f"doc_map: document_id DUPLICADO: {dm['document_id']!r} ({dm.get('source_file')})")
        else:
            seen_docids.add(dm["document_id"])
        for e in dm.get("entries") or []:
            if e.get("role") not in ROLES:
                errors.append(f"doc_map[{dm.get('document_id')}]: role inválido {e.get('role')!r}")
            if e.get("scope") not in SCOPES:
                errors.append(f"doc_map[{dm.get('document_id')}]: scope inválido {e.get('scope')!r}")
            if e.get("scope") == "paginas" and not e.get("paginas"):
                errors.append(f"doc_map[{dm.get('document_id')}]: scope=paginas sin paginas[]")
            _check_ref("doc_map", dm.get("document_id", "?"), e.get("id", ""))
            _check_prov("doc_map", dm.get("document_id", "?"), e, added_by=False)
    for dr in _read_jsonl(catalog_dir / FILES["docrel"]):
        _check_prov("docrel", f"{dr.get('doc_a')}↔{dr.get('doc_b')}", dr, added_by=False)
        if dr.get("tipo") not in TIPOS_DOCREL:
            errors.append(f"docrel: tipo inválido {dr.get('tipo')!r}")
    return errors


def write_jsonl(name: str, rows: list[dict], catalog_dir: Path = CATALOG_DIR,
                validate_after: bool = True) -> None:
    """Escritura vía la puerta: serializa ordenado-estable y VALIDA el conjunto después
    (fix dúo s90: el docstring lo prometía y no lo hacía). Los writers escriben en orden
    de dependencia (products → aliases → …); `validate_after=False` SOLO para escrituras
    intermedias de un lote que valida al final."""
    catalog_dir.mkdir(parents=True, exist_ok=True)
    path = catalog_dir / FILES[name]
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True) for r in rows)
                    + ("\n" if rows else ""), encoding="utf-8")
    if validate_after:
        errs = validate(catalog_dir)
        if errs:
            raise ValueError(f"write_jsonl({name}): el catálogo queda INVÁLIDO "
                             f"({len(errs)} errores; primero: {errs[0]})")


def _main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    if len(sys.argv) < 2 or sys.argv[1] not in ("validate", "resolve"):
        print(__doc__)
        return 2
    if sys.argv[1] == "validate":
        errs = validate()
        for e in errs:
            print(f"[ERROR] {e}")
        n_files = sum(1 for f in FILES.values() if (CATALOG_DIR / f).exists())
        print(f"{len(errs)} error(es) | {n_files}/{len(FILES)} ficheros presentes en {CATALOG_DIR}")
        return 1 if errs else 0
    cat = load()
    for tok in sys.argv[2:]:
        print(f"{tok!r} → {cat.resolve(tok)}")
    return 0


if __name__ == "__main__":
    sys.exit(_main())
