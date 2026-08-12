# s320 — EL ELEFANTE re-dimensionado: lo que QUEDA del entity-linking (DEC-074/091b) — plan v2 (tras dúo r20)

> **v1→v2 (dúo r20: Sol 6 · Fable 5, 0 FP — el dúo sobre el PLAN, el sitio más barato
> para estar equivocado):**
> 1. **E2 re-declarada como APUESTA ESTRUCTURAL no-eval-driven** (Fable F2 + Sol M6):
>    DEC-093 MIDIÓ que cablear detector→catálogo gobernado no arregla golds (identidad
>    ⊥ cuello, DEC-094) — el valor de E2 es escala-30+ y matar la clase dual-path, y
>    sus gates son de **EQUIVALENCIA (Δ≈0 pre-registrado)** en sweep-39/famtie/
>    assessment, no de mejora. Además exige ANTES: inventario COMPLETO de lectores de
>    `catalog.py` (no solo el detector: models/manufacturers/brands alimentan voz, OEM
>    y clasificación) + política multi-marca, y solo entonces elegir brazo
>    (sustitución vs snapshot-derivado-con-recibo).
> 2. **Los gates de aceptación son los del CONTRATO §7, con umbral** (Sol M1): hp018
>    4/4 SIN regresar hp009 · hp011→Supra · PASS ±2 · 100% provenance + tally — no
>    solo el criterio de escala.
> 3. **E3 = F3a SOLO mono-producto** (Sol M2, contrato §F3): multi-producto =
>    multi-valor o paraguas, NUNCA colapso; F3b por-página sigue GATED out-of-scope.
>    «Corpus-wide» se retira del framing.
> 4. **E1: QA TOTAL de candidates, no muestras** (Sol M3, DEC-093: veneno alfanumérico
>    y promover mueve top_k budget): mi pre-filtrado/pre-clasificación abarata los
>    lotes de Alberto, pero la cobertura es total. Tamaños: los fija E0, no cifras de
>    s99b (Fable F4).
> 5. **Las «3 filas en bandeja» ERAN TRABAJO CERRADO** (Sol M4): DEC-150 las adjudicó
>    y aplicó el 22-jul (quarantine vaciada) — fuera del plan. Mi propio censo estaba
>    stale: regla C también para censos.
> 6. **E4 = SUSTITUIR el seed hardcoded** (Sol M5): clarify-por-divergencia YA vive en
>    producción vía `FAMILY_REGISTRY` (ZXe/ZXSe, conversation_policy_impl.py:177-180)
>    cuyo comentario promete «the durable version reads the catalog's variant table»
>    — E4 cumple esa promesa (una sola fuente), jamás añade una segunda vía.
> 7. Anclas corregidas (Fable F1/F3/F5): «#50»/«#49.2» eran numeración fantasma → las
>    anclas canónicas son las fases del contrato (`IDENTITY_CATALOG_CONTRACT.md` F4) ·
>    el gap doc_map es 853/1014 con el corte activo a precisar en E0 · E0 censa
>    TAMBIÉN la frescura del snapshot `model_catalog.json` (regenerado ~18-jul,
>    pre-Kidde).

**Mandato** (Alberto, 12-ago): «vamos a por el elefante», arrancable independiente de su
sentada (costuras declaradas: los gates medidos finales quieren el FULL post-sentada como
baseline; el DB-apply masivo es adjudicación suya).

## El hallazgo del censo que re-dimensiona el plan (4 lentes, 107 tool-calls, anclas en recibo)

**La fila «identidad» del LEVER_DIGEST (línea 24) está STALE**: dice «ADD sigue vivo,
fix aparcado» — pero DEC-148/149/152/153 (s278-s281) ejecutaron la mitad CATÁLOGO-SIDE:
census add-vs-replace de 845 unidades/1.707 queries, guard `all_members_consumable`,
quarantine versionada, y **el perfil C1 de producción EXIGE `IDENTITY_RESOLVE_POLICY=replace`
fail-fast** (release_profiles.py:329; baseline oficial s281 medido bajo replace; DEC-162h).
El «4-7 sesiones» del PLAN cuenta trabajo ya consumido. **Este plan es el RESTANTE real.**

## Lo que queda (con anclas del censo)

1. **DATOS** — el entity-linking propiamente: `doc_map` congelado desde el 22-jul (861
   entradas; los +74 docs Kidde/Casmar s314 SIN mapear; 149 activos sin entrada en s281,
   cobertura actual NO medida) · candidates ~630 sin QA (T1 ≈363 de incendios, DEC-093:
   adjudicar NO es inerte) · 3 filas del census s278 en bandeja de Alberto
   (FAAST/ZXR/G-100-R).
2. **EL DOBLE CATÁLOGO (estructural, el frankenstein real que queda)**: el detector de
   PRODUCCIÓN vive de `model_catalog.json` (591 modelos, snapshot NO gobernado regenerado
   del corpus) mientras el resolver gobernado es OTRO extractor (DEC-093, explícito). Dos
   fuentes de identidad = la clase dual-path que PR-C acaba de matar en serving.
3. **F3 re-tag DOC completo**: solo campañas parciales (T3=221 chunks; parches s314/s315);
   pm-genérico global NO censado (el s315 umbralizaba ≥3 menciones); T2 residual 605
   doc_type NULL / 769 language NULL; unknown post-lote-Kidde sin re-censar.
4. **Activos F1 sin consumidor** (censo lente 2): `relations` (42), `docrel` (9, los pares
   ES/EN), `doc_map.paginas` (dato muerto), `vendido_bajo`/`oem_manufacturer_marca` —
   consumirlos o retirarlos HONESTAMENTE, no dejarlos de cera.
5. **Clarify-on-ambiguity conduct-level**: diferido en s91 (enmienda: por-PREGUNTA, no
   por-flag); `divergent` es metadato adjudicado que nadie consume aún.
6. **Higiene de cierre**: retirar `identity_index.py`+`IDENTITY_MAP` (legacy, 0 tests, #50)
   · graduar `IDENTITY_RESOLVE`/`POLICY` (default código=off/add vs producción=on/replace —
   la clase r18) · companions s285 fuera de la puerta · productización del detector para
   ingesta-30+ (#49.2) + **DRY-RUN del criterio de escala: fabricante nuevo ≤~15 min de
   Alberto — si no se cumple, el workstream FALLA aunque los golds pasen (contrato §7)**.

## Fases propuestas (≈3-5 sesiones, no 4-7)

- **E0 — censo fresco de datos ($0, media sesión)**: cobertura real de doc_map post-Kidde ·
  pm-genérico global sin umbral · unknown post-s314 · candidates por familia. Recibo que
  fija las cifras que E1-E3 consumen. + fix de la fila stale del LEVER_DIGEST.
- **E1 — completar los DATOS (1 sesión + lotes de Alberto en paralelo)**: doc_map para los
  +74 y la clase sin-entrada (auto-candidatos con evidencia, packet de adjudicación) ·
  packet T1 de candidates pre-filtrado (los ~363 de incendios, muestras QA de 30-60) ·
  las 3 filas s278. Los packets van llegando a la sentada de Alberto; nada se aplica solo.
- **E2 — matar el doble catálogo (1-2 sesiones, dúo, la pieza ALTO)**: el detector de
  producción consume el catálogo GOBERNADO (o su snapshot se REGENERA desde él con recibo
  de equivalencia). Gates: sweep-39 + famtie freeze-contract + assessment smoke + replay.
- **E3 — F3 re-tag completo (1 sesión)**: dry-run corpus-wide de pm canónico → packet
  DB-apply (adjudicación Alberto, patrón DP312x a escala) → apply con recibo reversible.
- **E4 — cierre (1 sesión)**: clarify por-pregunta (si E0-E1 muestran población que lo
  justifique — si no, NO se cablea: pregunta cero) · consumo-o-retiro de relations/docrel ·
  graduación de flags de identidad · retiro identity_index/#50 · #49.2 + dry-run de escala.

**Costuras con la sentada** (declaradas): E1/E3 EMITEN packets que su sentada consume;
los gates E2/E3 se miden contra el FULL fresco post-sentada. E0 arranca YA.

## Gaps declarados

- El valor en producción de IDENTITY_RESOLVE se verificará por Railway API antes de E2
  (no inferir; el perfil C1 lo exige pero la var manda).
- La cobertura doc_map «desconocida» es exactamente lo que E0 mide — este plan no promete
  cifras que no tiene.
- El criterio de escala (≤15 min/fabricante) es EL criterio del workstream; E4 lo mide con
  dry-run real, no con estimación.
