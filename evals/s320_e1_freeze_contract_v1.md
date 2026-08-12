# s320 E1 — FREEZE-CONTRACT del gate de escritura tier-A (pre-registrado)

**Regla** (r22 Sol M4, contrato `IDENTITY_CATALOG_CONTRACT.md` §freeze): NINGUNA
entrada de doc_map se escribe sin este artefacto congelado ANTES de la medición.

## Qué se congela

| Elemento | Valor |
|---|---|
| Catálogo PRE | commit de `data/catalog/` en `claude/s320b-e1` HEAD pre-escritura |
| Catálogo POST | el commit de la escritura tier-A (46 entradas propuestas) |
| Corpus/índice | `chunks_v2` vivo (26.215 chunks, censo E0) — sin re-embedding |
| Config servida | perfil C1 v4: `IDENTITY_RESOLVE=on` + `IDENTITY_RESOLVE_POLICY=replace` + guard candidate-member (la config de PRODUCCIÓN verificada, no la de código) |
| Queries | UNA por doc tier-A: el pm literal del documento (46 queries, congeladas en el recibo de la sonda) |
| Métrica PRIMARIA | `allowed_sources`: PRE la sonda debe dar el doc AUSENTE; POST debe darlo PRESENTE — 46/46 esperado (el efecto es AÑADIR alcance por diseño) |
| No-regresión | sweep de los 39 golds: composición de pools OFF↔ON sin cambio atribuible (Δ dentro del jitter base medido; el Δ≈0 es NO-informativo como evidencia positiva — Fable r22 F4 — y por eso es secundaria) |
| Aborto | cualquier gold del sweep con cambio de composición fuera del jitter → NO se mergea; investigación antes |

## Qué NO valida este gate (declarado)

- No valida que el pm de la ingesta sea CORRECTO (eso es tier-A por construcción:
  triple coincidencia exact/alias + prefijo de marca + vendido_bajo).
- No mide efecto en PASS ni fact-level (identidad ⊥ cuello, DEC-094): el gate es
  de ALCANCE + no-regresión, coherente con el plan v2 (E2 apuesta estructural).
- Los tiers B/C/no-producto NO se escriben: van a packet de adjudicación.
