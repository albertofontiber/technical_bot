# s331 — Residuo E1 v2 (POST-DÚO): las 3 preguntas delegadas + atestación TI-007 + baja FR

**SUPERSEDE a `evals/s331_residuo_e1_propuesta_v1.md`** (la versión que atacó el dúo). Cambios de
esta v2 = los hallazgos del dúo aplicados. Dúo r38: Sol xhigh 5/5 confirmados (0 FP, max=crítico) +
Fable 4/4 confirmados (0 FP, max=medio) — **pairing roto por drift del árbol en vuelo** (el autor
escribió plan/censo mientras Sol corría; clase TECH_DEBT #86; la review de Fable quedó guardada sin
emparejar: `evals/adversarial_reviews/2026-08-20T19-51-45_claude-fable-5_a2d62a089e9b.md`).

## Lo que el dúo cambió (correcciones aplicadas aquí)

1. **[Sol crítico] La premisa «serie FS2 no existe» era FALSA.** El corpus tiene el manual activo
   `FS2-1` (997-158, ene-2002: «Centrales de incendios convencionales de 1, 2 y 4 zonas»), en
   catálogo `notifier:fs-1/fs-2/fs-4` (candidates, provenance s83:FS2-1) con doc_map adjudicado.
   Mi censo buscó la grafía `fs2` en ids/pm y era ciego a `fs-1`. **Hecha la comparación al píxel
   que la pregunta de Alberto pedía** (ambos PDF delante):
   | rasgo | FS-1/FS-2/FS-4 (FS2-1.pdf) | guía MADT015_01 |
   |---|---|---|
   | zonas | 1 / 2 / 4 | leds Zona 1..8; EFL «(x2, x4, x8)» |
   | final de línea | SOLO resistencia 4K7 (ref. 020-417) | resistencia 4K7 **o condensador 0,47µF** seleccionable |
   | entradas | solo Class Change | **2 entradas digitales** configurables (7 tipos) |
   | retardos | no tiene | principal/secundario 0-10 min + coincidencia |
   | interfaz | llave + Rearme/Avance/Estado | teclas numéricas 1-5, niveles de acceso, código [1][5][1] |
   La guía NO puede ser de la serie FS; su árbol de configuración es idéntico 1:1 al del anexo
   `MADT015_03` («Anexo al manual de instalación de la central **NFS 2-8**, ref.: MI-DT-015»).
   **La conclusión D1 (NFS 2-8) sobrevive, ahora con la comparación hecha, no supuesta.**
2. **[Sol medio] Los retags DB NO son persistentes**: la re-ingesta re-deriva pm
   (`detect_document_metadata`, filename-first — por eso TI-007 recayó a `TI-007` aunque su
   filename contiene VSN-4REL) y `apply_metadata` lo estampa en los chunks. → Se registra deuda
   nueva **TECH_DEBT #94** (autoridad de pm gobernada consumida en B5); los retags de hoy arreglan
   el serving VIGENTE y quedan protegidos por la deuda declarada, no por fe.
3. **[Sol medio + Fable medio] El censo GD2 era circular** (solo docs con pm SMART*). Re-hecho
   **corpus-wide** (1.054 activos — paginado: la 1ª pasada truncaba a 1.000, otro hallazgo del
   control): las únicas menciones GD2/GD3/GD-2/GD-3 son 6 docs Detnov donde la cadena es
   «P**GD-2**00» (el programador de direcciones). **Veredicto cerrado: el doc del SMART3 GD2 NO
   está en el corpus; el GD3 = SMART3G-D3 sí está atestado (doc MTEX4805 Zona 2).**
4. **[Sol medio] El fallback «pm-only si el dúo tumba el doc_map» era incoherente** con el gate de
   findability. ELIMINADO: D1 es un PAR ATÓMICO retag+doc_map; si cae uno, cae el par.
5. **[Fable medio] La findability de D1 era autosatisfecha por construcción** (la fila de doc_map
   que la satisface la añade el propio plan → el gate no podía fallar = ritual). Corregido en el
   writer con modos OPT-IN por fila (los planes viejos no cambian de semántica):
   `findability: "modelo_independiente"` → si la única entry que casa la añadió este plan, se
   declara `autosatisfecha_por_el_plan` y el gate EXIGE además que el pm nuevo resuelva en el
   catálogo PREVIO al plan (`C.normkey(pm) ∈ _resolvable_terms(antes)` — NFS 2-8 y VSN-4REL
   resuelven: productos activos no-candidate preexistentes);
   `findability: "na_unknown"` → válido SOLO con pm_nuevo == "unknown", declarado en recibo.
6. **[Sol menor] Cita legal de idiomas corregida**: la política es RULER_DESIGN (scope del answer
   ES+EN; FR fuera) + política s65 — NO DEC-066 (que es el pre-filtro family-aware NO-OP).
7. **[Fable menor] «El writer» ya no es promesa**: se reutiliza el writer PARAMETRIZADO existente
   `scripts/s324_lote_firmado_writer.py --plan evals/s331_residuo_plan_v1.json` (freeze + dry-run
   + censo del radio de explosión + CAS + rollback ya validados en s324) con la extensión (5), y
   las bajas van por `scripts/s324_retirar_docs.py --lote s331` (guardas + recibo + reversión).
   Condición de firma intacta: dry-run PASS con recibo ANTES de --aplicar.

## Decisiones (sin cambios de fondo respecto a v1, con la evidencia reforzada)

- **D1** `MADT015_01` (18 chunks): retag pm `MADT-015` → `NFS 2-8` **+** doc_map
  `notifier:nfs-2-8` (par atómico; provenance declara adjudicación delegada + evidencia documental
  hermana; sin cita full-text propia — como MADT731_06 en s324c, con la diferencia declarada:
  aquello fue adjudicación explícita de Alberto con URL, esto es delegación).
- **D2** `MNDT600` (16 chunks): retag pm → `unknown`; sin doc_map (R4). Paraguas SMART 3 =
  decisión aparte de Alberto (no necesaria para limpiar el artefacto).
- **D3** `MNDT701` (6 chunks): retag pm → `unknown`; doc_map DIFERIDO al ítem 3 («nombres con
  barra»: 20/20MI, 20/20R; grafía verbatim del corpus «S20/20MI»).
- **D4** TI-007 (2 chunks): retag chunks `TI-007` → `VSN-4REL` (documents.pm ya es VSN-4REL; el
  CAS de documents es un no-op mismo-valor) **+** doc_map `notifier:vsn-4rel` con cita full-text
  «Instalación del módulo VSN-4REL». Ejecuta la adjudicación registrada (#87).
- **D5** baja `996-130-000-3 Manuel d'utilisation ZX_hlsi` (1 chunk FR): firmada por Alberto en la
  fila §1.A del packet. Sin hermano ES del mismo manual (declarado); reversible.
- **VSN2-PLUS**: dossier `evals/s331_vsn2plus_censo_v1.md`, CERO escrituras (rebrand multi-marca →
  sentada E1b).

## Gaps que siguen declarados

- D1 sin cita en el contenido propio (evidencia documental; par atómico, sin fallback).
- `unknown` en D2/D3 renuncia al vínculo de producto HOY (diferido con mecanismo nombrado).
- Los 4 retags decaen si esos docs se re-ingestan (deuda #94; el recibo lo declara).
- Radio de explosión esperado en el detector: 0 términos entran/salen; si el dry-run muestra otra
  cosa → STOP.
