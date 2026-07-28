-- ============================================================================
-- s285 · H0-T3 FINAL — paquete de aplicación de las 26 adjudicaciones de Alberto
-- ============================================================================
-- Origen de la adjudicación : Alberto (lote H0, s282→s285), sobre el packet
--                             `evals/s281_h0t3_retag_packet_v1.md` §4.
-- Informe de esta lane      : `evals/s285_t3_final_report_v1.md`
-- Recibo de verificación DB : `evals/s285_t3_final_verify_v1.json` (READ-ONLY)
--
-- ESTADO: PROPUESTA. Ninguna sentencia de este fichero ha sido ejecutada.
--         La lane que lo generó operó SELECT-only (PostgREST GET), $0 LLM.
--
-- ── VERIFICACIÓN EN VIVO (2026-07-25, chunks_v2=25090 · documents=1171) ──────
--   · Los 26 source_file de Alberto matchean EXACTO en chunks_v2 (0 discrepancias).
--   · Los 26 suman EXACTAMENTE los 227 chunks que hoy quedan con
--     product_model='unknown' en TODO el corpus (0 NULL, 0 '').
--   · HALLAZGO: los bloques §2 (migración simétrica ZXe/ZXSe) y §3 (NSRE24, la
--     única confianza ALTA) del packet s281 YA ESTÁN APLICADOS en la DB viva:
--       MIE-MI-600 = 'ZXSe' (88) · MIE-MI-{530,MP-530,MU-530,MP-535} = 'ZXe' (207)
--       'ZX2e/ZX5e' = 0 filas · 'ZX2e y ZX5e' = 0 filas · NSRE24 = 'NSRE24' (3)
--     La tabla de respaldo `_s281_h0t3_backup` NO existe (404 en PostgREST) → esos
--     dos bloques se aplicaron SIN pre-imagen. NO re-ejecutarlos. Su rollback
--     directo está documentado en el packet s281 §2.6.
--
-- ── CONVENCIÓN DE ETIQUETA (derivada de las adjudicaciones + código verificado) ──
--   (a) FAMILIA-genérica cuando el manual cubre UNA familia definida (s281 §2:
--       'ZXe', 'ZXSe'; aquí: 'DX').
--   (b) COMPUESTO cuando el manual documenta VARIOS productos distintos.
--       Separador '/' por defecto; ' y ' cuando algún miembro contiene '/'
--       (precedente vivo en el corpus: 'ZX2e y ZX5e', 'NX2/R/R y NX5/R/R').
--   (c) Por qué el compuesto NO rompe la findability por miembro (verificado en
--       código, no asumido):
--         · retriever.model_to_imatch_pattern() → `\y<core>(?!\d)`: '/' y ' ' son
--           frontera de palabra en ARE, así que `\yNFS[- ]*Supra(?!\d)` casa dentro
--           de 'NFS Supra/Vision Plus2/ESS-2Plus'.
--         · series_registry.normalize_model() quita SOLO '-' y ' ' → el core del
--           miembro sigue siendo SUBSTRING del tag compuesto normalizado, que es
--           exactamente la regla de nivel-1 de _filter_to_query_models().
--           Comprobado: 'ms1' ⊂ 'ms1/ms2/ms4' · 's/2t1' ⊂ 's/2t1ys/3t1' ·
--           'nx2/r/r' ⊂ 'nx2/r/rynx5/r/r' · 'nco10' ⊂ 'nco10/nco100/vsnco'.
--         · La etiqueta FAMILIA sí pierde el match por MIEMBRO en ese canal
--           ('dx1' ⊄ 'dx') — es el trade-off ya adjudicado en s281 §2.3; los
--           miembros llegan por el resolver gobernado (Canal A, allowed_sources).
--
-- ── ORDEN DE EJECUCIÓN ──────────────────────────────────────────────────────
--   0) §0 respaldo pre-imagen (OBLIGATORIO, una sola vez)
--   1) §1 bloques ejecutables (20 fichas · 221 chunks) + §2 manufacturer
--   2) §3 verificación de conteos
--   3) §4 los 3 [CONFIRMAR-ALBERTO] — COMENTADOS, no ejecutar sin su visto
--   4) §5 opcionales declarados — COMENTADOS
--   5) GATE de eval OBLIGATORIO (ver §6) ANTES de dar el tramo por bueno
--   6) §7 rollback exacto si el gate regresa
--
-- NOTA HNSW (lección s78): los UPDATE masivos re-insertan cada fila en el grafo
-- HNSW y pueden dar `statement timeout`. Aquí el bloque mayor es de 30 filas, muy
-- por debajo del umbral que lo disparó (cientos). Si alguno diera timeout: trocear
-- con `AND id IN (...)` en lotes de 10.
-- ============================================================================


-- ════════════════════════════════════════════════════════════════════════════
-- §0 · RESPALDO PRE-IMAGEN (ejecutar UNA vez, antes de nada)
-- ════════════════════════════════════════════════════════════════════════════
-- Cubre los 227 chunks de las 26 fichas — incluidos los 3 [CONFIRMAR], el
-- no-tocar (#19) y los 2 a borrar — para que el rollback sea total y no dependa
-- de que el valor previo fuera uniforme.

CREATE TABLE IF NOT EXISTS _s285_t3_backup AS
SELECT id,
       source_file,
       product_model AS product_model_prev,
       manufacturer  AS manufacturer_prev,
       now()         AS snapshot_at
FROM chunks_v2
WHERE source_file IN (
    'FS2-1',
    'ms1-2-4',
    'Manual-de-Usuario-S3-T1-y-S-2-T1',
    'Manual-de-Usuario-S3-T2-y-S2-T2',
    'I56-2006-004 MI-DMMI_DMM2I_D2ICMO',
    'BANI-G-24_Eng',
    'LocatorPlus-Installation-Manual-1.3',
    'I56-3388-002 NFX-OPT_multi',
    'I56-4406-001 MI-DMMIE MI-DMM2IE MI-D2ICMOE',
    'I56-3389-002 NFX-SMT2_multi',
    'Manual_DXD-2X0 (55321002 MI 607 m 2024 c)',
    'I56-5005-002_D Notifier Sounder Strobe',
    'MIE-MP-525rv1',
    'I56-5004-000-Notifier-Strobe',
    'HLSI-MA-025 Guia Rapida NFS_Supra_XP_c',
    'D700-3-Sp',
    'Manual Pulsador convencional IP65 PCD-100WP (1)',
    'Compatibilidad-detectores-de-monoxido-NCO10-NCO100-VSN-CO',
    'Compatibilidad-entre-equipos-Notifier-y-Morley',
    'Configuracion-entrada-digital-de-la-central-NFS-Supra-VSN-Plus2-ESS-2Plus',
    'Docs Morley-IAS Lite&Plus - QR',
    'EMA24RS2R_NX2y5-R-R',
    'Finales-de-linea-de-las-centrales-convencionales',
    'No-puedo-conectarme-con-el-ordenador-a-la-central-ZX',
    'RP1R-SUPRA-VSN-RP1R-PLUS2-Teclado-bloqueado',
    'Solicitud-asistencia-curso-de-formacion-puesta-en-marcha-consultas-tecnica'
);

-- GATE DEL RESPALDO — debe dar EXACTAMENTE 227 y 26:
SELECT count(*) AS filas_respaldadas,               -- esperado: 227
       count(DISTINCT source_file) AS ficheros,     -- esperado: 26
       count(*) FILTER (WHERE product_model_prev <> 'unknown') AS no_unknown  -- esperado: 0
FROM _s285_t3_backup;


-- ════════════════════════════════════════════════════════════════════════════
-- §1 · BLOQUES EJECUTABLES — 20 fichas · 221 chunks
-- ════════════════════════════════════════════════════════════════════════════
-- Cada bloque lleva su conteo esperado, VERIFICADO contra la DB viva el 2026-07-25.

-- ── #1 · FS2-1 · 30 chunks ──────────────────────────────────────────────────
-- Alberto: modelo FS, variantes FS-1/FS-2/FS-4 ("centrales convencionales de 1, 2
-- y 4 zonas"; "1 zona"=FS-1). El filename 'FS2-1' está MAL NOMBRADO → no se usa
-- como etiqueta (el doc-level pm='FS2-1' queda superado por esta adjudicación).
UPDATE chunks_v2 SET product_model = 'FS-1/FS-2/FS-4'
 WHERE source_file = 'FS2-1' AND product_model = 'unknown'
 RETURNING id;  -- esperado: 30 filas

-- ── #2 · ms1-2-4 · 29 chunks ────────────────────────────────────────────────
-- Alberto: MS-1/MS-2/MS-4 (Morley). El técnico puede escribir "MS1" sin guión →
-- cubierto por normalize_model (quita '-'), y en el catálogo gobernado por
-- norm_token (idem) → el alias de catálogo es documental, no funcional (ver
-- `data/catalog/s285_t3_alias_companion.jsonl` y el informe §alias).
UPDATE chunks_v2 SET product_model = 'MS-1/MS-2/MS-4'
 WHERE source_file = 'ms1-2-4' AND product_model = 'unknown'
 RETURNING id;  -- esperado: 29 filas

-- ── #3 · Manual-de-Usuario-S3-T1-y-S-2-T1 · 28 chunks ───────────────────────
-- Alberto: S/2-T1 y S/3-T1 (Fidegas). Separador ' y ' porque los MIEMBROS
-- contienen '/' (usar '/' daría 'S/2-T1/S/3-T1', ilegible y ambiguo).
UPDATE chunks_v2 SET product_model = 'S/2-T1 y S/3-T1'
 WHERE source_file = 'Manual-de-Usuario-S3-T1-y-S-2-T1' AND product_model = 'unknown'
 RETURNING id;  -- esperado: 28 filas

-- ── #4 · Manual-de-Usuario-S3-T2-y-S2-T2 · 24 chunks ────────────────────────
-- Alberto: S/3-T2 y S/2-T2. Los otros códigos s83 (00051/00052/03382/03383) son
-- repuestos/accesorios — simplicidad ADJUDICADA: solo los 2 modelos.
UPDATE chunks_v2 SET product_model = 'S/3-T2 y S/2-T2'
 WHERE source_file = 'Manual-de-Usuario-S3-T2-y-S2-T2' AND product_model = 'unknown'
 RETURNING id;  -- esperado: 24 filas

-- ── #5 · I56-2006-004 MI-DMMI_DMM2I_D2ICMO · 17 chunks ──────────────────────
UPDATE chunks_v2 SET product_model = 'MI-DMMI/MI-DMM2I/MI-D2ICMO'
 WHERE source_file = 'I56-2006-004 MI-DMMI_DMM2I_D2ICMO' AND product_model = 'unknown'
 RETURNING id;  -- esperado: 17 filas

-- ── #6 · BANI-G-24_Eng · 16 chunks ──────────────────────────────────────────
-- Alberto: IS 28 Mk 4 (coincide con el doc-level ya gobernado; s83 dice
-- 'IS 28 Mk 4 Banshee' — 'Banshee' es la familia comercial, no el modelo).
UPDATE chunks_v2 SET product_model = 'IS 28 Mk 4'
 WHERE source_file = 'BANI-G-24_Eng' AND product_model = 'unknown'
 RETURNING id;  -- esperado: 16 filas

-- ── #7 · LocatorPlus-Installation-Manual-1.3 · 16 chunks (pm + manufacturer) ──
-- Alberto: LocatorPlus (código SLP-001), marca Signaline — TAMBIÉN manufacturer.
-- El código SLP-001 NO va al pm (es número de parte): ya vive como alias en
-- `data/catalog/aliases.jsonl` apuntando a signaline:signaline-locatorplus
-- (VERIFICADO presente y consumible).
UPDATE chunks_v2 SET product_model = 'LocatorPlus'
 WHERE source_file = 'LocatorPlus-Installation-Manual-1.3' AND product_model = 'unknown'
 RETURNING id;  -- esperado: 16 filas
-- (el UPDATE de manufacturer de esta ficha va en §2 — cambia un eje distinto)

-- ── #8 · I56-3388-002 NFX-OPT_multi · 9 chunks ──────────────────────────────
UPDATE chunks_v2 SET product_model = 'NFX-OPT/NFXI-OPT'
 WHERE source_file = 'I56-3388-002 NFX-OPT_multi' AND product_model = 'unknown'
 RETURNING id;  -- esperado: 9 filas

-- ── #9 · I56-4406-001 MI-DMMIE MI-DMM2IE MI-D2ICMOE · 9 chunks ──────────────
UPDATE chunks_v2 SET product_model = 'MI-DMMIE/MI-DMM2IE/MI-D2ICMOE'
 WHERE source_file = 'I56-4406-001 MI-DMMIE MI-DMM2IE MI-D2ICMOE' AND product_model = 'unknown'
 RETURNING id;  -- esperado: 9 filas

-- ── #10 · I56-3389-002 NFX-SMT2_multi · 7 chunks ────────────────────────────
UPDATE chunks_v2 SET product_model = 'NFX-SMT2/NFXI-SMT2'
 WHERE source_file = 'I56-3389-002 NFX-SMT2_multi' AND product_model = 'unknown'
 RETURNING id;  -- esperado: 7 filas

-- ── #11 · Manual_DXD-2X0 (55321002 MI 607 m 2024 c) · 7 chunks ──────────────
-- Alberto: DTD-210, DTD-215, DOD-220, DOTD-230 (orden del propio manual).
UPDATE chunks_v2 SET product_model = 'DTD-210/DTD-215/DOD-220/DOTD-230'
 WHERE source_file = 'Manual_DXD-2X0 (55321002 MI 607 m 2024 c)' AND product_model = 'unknown'
 RETURNING id;  -- esperado: 7 filas

-- ── #12 · I56-5005-002_D Notifier Sounder Strobe · 6 chunks ─────────────────
-- Alberto: WRA-xC-I02 y WWA-xC-I02 (x = P|R según color) + aliases CONCRETOS al
-- catálogo.
-- DESVIACIÓN MÍNIMA DECLARADA respecto de la letra, con medida: escribir el
-- placeholder 'x' en el pm ROMPE el matching por SKU concreta —
-- normalize_model('WRA-xC-I02') = 'wraxci02' y 'wrapci02' NO es substring suyo,
-- así que `_filter_to_query_models` tiraría el chunk ante la query "WRA-PC-I02".
-- La lista concreta contiene la MISMA información y sí casa. Si Alberto prefiere
-- la letra, usar la línea alternativa comentada (y asumir el gap de matching).
UPDATE chunks_v2 SET product_model = 'WRA-PC-I02/WRA-RC-I02/WWA-PC-I02/WWA-RC-I02'
--   ALTERNATIVA (letra estricta):  SET product_model = 'WRA-xC-I02/WWA-xC-I02'
 WHERE source_file = 'I56-5005-002_D Notifier Sounder Strobe' AND product_model = 'unknown'
 RETURNING id;  -- esperado: 6 filas

-- ── #13 · MIE-MP-525rv1 · 6 chunks ──────────────────────────────────────────
-- Alberto: familia DX (DX1/DX2/DX4) → etiqueta FAMILIA 'DX' (convención
-- adjudicada) + miembros al catálogo.
-- OJO (declarado, no bloqueante): la familia-genérica pierde el match por MIEMBRO
-- en el canal keyword/model-filter ('dx1' ⊄ 'dx'), igual que ZXe en s281 §2.3;
-- los miembros deben llegar por el catálogo gobernado. HOY el paraguas 'DX' NO
-- existe en `data/catalog/umbrellas.jsonl` (sí 'Dimension'/'serie Dimension', que
-- agrupa la generación DX1e/DX2e/DX4e — NO es la misma) y morley:dx2 no existe
-- (el token 'DX2' está aliaseado a morley:dx2e). Ver informe §catálogo-bloqueado.
UPDATE chunks_v2 SET product_model = 'DX'
 WHERE source_file = 'MIE-MP-525rv1' AND product_model = 'unknown'
 RETURNING id;  -- esperado: 6 filas

-- ── #14 · I56-5004-000-Notifier-Strobe · 5 chunks ───────────────────────────
-- Alberto: WRL-xC-I02, WWL-xC-I02 (mismo esquema x=P|R). Misma desviación
-- declarada que #12 y por la misma medida.
UPDATE chunks_v2 SET product_model = 'WRL-PC-I02/WRL-RC-I02/WWL-PC-I02/WWL-RC-I02'
--   ALTERNATIVA (letra estricta):  SET product_model = 'WRL-xC-I02/WWL-xC-I02'
 WHERE source_file = 'I56-5004-000-Notifier-Strobe' AND product_model = 'unknown'
 RETURNING id;  -- esperado: 5 filas

-- ── #15 · HLSI-MA-025 Guia Rapida NFS_Supra_XP_c · 4 chunks ─────────────────
-- Alberto: NFS Supra, Vision Plus2, ESS 2Plus (equivalencias: Vision Plus2 =
-- VSN-Plus2 ; ESS 2Plus = ESS-2Plus → aliases).
-- REALIZACIÓN DE LA EQUIVALENCIA EN ESTE CAMPO (medida): normalize_model quita
-- solo '-' y ' ', así que 'ESS 2Plus' ≡ 'ESS-2Plus' ('ess2plus') pero
-- 'Vision Plus2' ('visionplus2') ≢ 'VSN-Plus2' ('vsnplus2'). Para que AMBAS
-- superficies que un técnico escribe alcancen el doc, el compuesto lleva las dos.
-- Si Alberto prefiere la letra estricta, usar la alternativa comentada.
UPDATE chunks_v2 SET product_model = 'NFS Supra/Vision Plus2/VSN-Plus2/ESS-2Plus'
--   ALTERNATIVA (letra estricta):  SET product_model = 'NFS Supra/Vision Plus2/ESS 2Plus'
 WHERE source_file = 'HLSI-MA-025 Guia Rapida NFS_Supra_XP_c' AND product_model = 'unknown'
 RETURNING id;  -- esperado: 4 filas

-- ── #16 · D700-3-Sp · 3 chunks ──────────────────────────────────────────────
-- Alberto: MCP1A-x, MCP1B-x, MCP2A-x, MCP2B-x, MCP3A-x, MCP4A-x (sufijo variable).
-- Aquí la letra SÍ se respeta tal cual: el placeholder es SUFIJO, así que el core
-- del modelo base sigue casando ('mcp1a' ⊂ 'mcp1ax…' — verificado). No se
-- enumeran los valores de x: NO están en la fuente (el manual escribe "MCP1...",
-- "MCP2...") → enumerarlos sería invención.
UPDATE chunks_v2 SET product_model = 'MCP1A-x/MCP1B-x/MCP2A-x/MCP2B-x/MCP3A-x/MCP4A-x'
 WHERE source_file = 'D700-3-Sp' AND product_model = 'unknown'
 RETURNING id;  -- esperado: 3 filas

-- ── #17 · Manual Pulsador convencional IP65 PCD-100WP (1) · 2 chunks ────────
-- Alberto: Waterproof ReSet Call Point 01/02/11 (literal del título del manual).
-- Declarado: los canonicals del catálogo son 'Waterproof ReSet Series 01/02' y
-- 'Waterproof ReSet 11' → NO casan por substring con este tag; el puente son los
-- 3 aliases del companion (efecto=funcional).
UPDATE chunks_v2 SET product_model = 'Waterproof ReSet Call Point 01/02/11'
 WHERE source_file = 'Manual Pulsador convencional IP65 PCD-100WP (1)' AND product_model = 'unknown'
 RETURNING id;  -- esperado: 2 filas

-- ── #18 · Compatibilidad-detectores-de-monoxido-NCO10-NCO100-VSN-CO · 1 chunk ─
-- Alberto: NCO10, NCO100, VSN-CO. Doc de COMPATIBILIDAD → ver el análisis de la
-- lane COMPATIBILITY_BUNDLE_COVERAGE en el informe §4 (resumen: con el tag puesto
-- el doc deja de ser invisible al model-filter; la lane fail-closed sigue sin
-- poder usarlo como bundle porque es 1 chunk y no cubre los 3 facets exigidos).
UPDATE chunks_v2 SET product_model = 'NCO10/NCO100/VSN-CO'
 WHERE source_file = 'Compatibilidad-detectores-de-monoxido-NCO10-NCO100-VSN-CO'
   AND product_model = 'unknown'
 RETURNING id;  -- esperado: 1 fila

-- ── #19 · Compatibilidad-entre-equipos-Notifier-y-Morley · SIN CAMBIO ───────
-- Alberto: SIN modelo, aplica genéricamente (Morley↔Notifier NO son compatibles).
-- NO se re-taguea. El análisis del riesgo de exclusión + las opciones están en el
-- informe §4. Se deja el chunk como está (product_model='unknown').

-- ── #20 · Configuracion-entrada-digital-...-NFS-Supra-VSN-Plus2-ESS-2Plus · 1 ─
-- Alberto: NFS Supra, Vision Plus2, ESS 2Plus (mismas equivalencias que #15) →
-- MISMA etiqueta que #15 (consistencia entre los dos docs de la misma central).
UPDATE chunks_v2 SET product_model = 'NFS Supra/Vision Plus2/VSN-Plus2/ESS-2Plus'
--   ALTERNATIVA (letra estricta):  SET product_model = 'NFS Supra/Vision Plus2/ESS 2Plus'
 WHERE source_file = 'Configuracion-entrada-digital-de-la-central-NFS-Supra-VSN-Plus2-ESS-2Plus'
   AND product_model = 'unknown'
 RETURNING id;  -- esperado: 1 fila

-- ── #22 · EMA24RS2R_NX2y5-R-R · 1 chunk ─────────────────────────────────────
-- Alberto: NX2/R/R y NX5/R/R ("ojo barras") → separador ' y ' (los miembros
-- contienen '/'). Coincide EXACTAMENTE con el doc-level ya gobernado.
UPDATE chunks_v2 SET product_model = 'NX2/R/R y NX5/R/R'
 WHERE source_file = 'EMA24RS2R_NX2y5-R-R' AND product_model = 'unknown'
 RETURNING id;  -- esperado: 1 fila

-- (#21 y #26 → ELIMINACIÓN: `evals/s285_t3_deletions_proposal_v1.sql`)
-- (#23, #24, #25 → §4 de este fichero, COMENTADOS hasta el visto de Alberto)


-- ════════════════════════════════════════════════════════════════════════════
-- §2 · MANUFACTURER (único eje-marca adjudicado en el lote) — 16 chunks
-- ════════════════════════════════════════════════════════════════════════════
-- #7 · Alberto: «marca Signaline (¡también manufacturer!)».
-- VERIFICADO en DB: hoy 'LGM Products' tiene 35 chunks en 2 docs
--   — LocatorPlus-Installation-Manual-1.3   (16, esta ficha)
--   — LocatorPlus-EN-Installation-Manual-1.0 (19, NO está en el lote de Alberto)
-- y 'Signaline' NO existe hoy como manufacturer en chunks_v2 (32 marcas distintas).
-- CONSECUENCIA DECLARADA: aplicar solo esta ficha deja los dos manuales del MISMO
-- producto con marcas distintas. Ver el bloque OPCIONAL-B de §5.
UPDATE chunks_v2 SET manufacturer = 'Signaline'
 WHERE source_file = 'LocatorPlus-Installation-Manual-1.3' AND manufacturer = 'LGM Products'
 RETURNING id;  -- esperado: 16 filas


-- ════════════════════════════════════════════════════════════════════════════
-- §3 · VERIFICACIÓN DE CONTEOS (ejecutar tras §1+§2)
-- ════════════════════════════════════════════════════════════════════════════

-- 3.1 · Ninguna de las 20 fichas debe quedar con 'unknown':
SELECT source_file, count(*) AS chunks, count(*) FILTER (WHERE product_model='unknown') AS aun_unknown
FROM chunks_v2
WHERE source_file IN (
    'FS2-1','ms1-2-4','Manual-de-Usuario-S3-T1-y-S-2-T1','Manual-de-Usuario-S3-T2-y-S2-T2',
    'I56-2006-004 MI-DMMI_DMM2I_D2ICMO','BANI-G-24_Eng','LocatorPlus-Installation-Manual-1.3',
    'I56-3388-002 NFX-OPT_multi','I56-4406-001 MI-DMMIE MI-DMM2IE MI-D2ICMOE',
    'I56-3389-002 NFX-SMT2_multi','Manual_DXD-2X0 (55321002 MI 607 m 2024 c)',
    'I56-5005-002_D Notifier Sounder Strobe','MIE-MP-525rv1','I56-5004-000-Notifier-Strobe',
    'HLSI-MA-025 Guia Rapida NFS_Supra_XP_c','D700-3-Sp',
    'Manual Pulsador convencional IP65 PCD-100WP (1)',
    'Compatibilidad-detectores-de-monoxido-NCO10-NCO100-VSN-CO',
    'Configuracion-entrada-digital-de-la-central-NFS-Supra-VSN-Plus2-ESS-2Plus',
    'EMA24RS2R_NX2y5-R-R')
GROUP BY source_file ORDER BY chunks DESC;
-- esperado: 20 filas · suma chunks = 221 · aun_unknown = 0 en TODAS

-- 3.2 · Saldo corpus-wide del tag 'unknown':
SELECT count(*) AS unknown_restantes FROM chunks_v2 WHERE product_model = 'unknown';
-- antes: 227 · esperado tras §1: 6
--   = 3 de los [CONFIRMAR] (#23,#24,#25) + 1 del no-tocar (#19) + 2 de los DELETE (#21,#26)
-- Tras §4 (los 3 CONFIRMAR) → 3.  Tras las 2 eliminaciones → 1 (solo #19, por diseño).


-- ════════════════════════════════════════════════════════════════════════════
-- §4 · [CONFIRMAR-ALBERTO] — 3 fichas · 3 chunks · NO EJECUTAR SIN SU VISTO
-- ════════════════════════════════════════════════════════════════════════════
-- Los tres son documentos de 1 chunk (blast radius mínimo, reversibles por §7).

-- ── #23 · Finales-de-linea-de-las-centrales-convencionales · 1 chunk ────────
-- Alberto: multi-FAMILIA → NFS (NFS2/NFS4/NFS8) + VSN-LT (2/4/8/12 lazos) +
-- VSN-PLUS Morley (VSN 2/4/8/12 PLUS). OJO: "VSN 2 PLUS" ≠ "VSN-Plus2" (Notifier).
--
-- RECOMENDACIÓN DE LA LANE: **enumerar los MIEMBROS** (opción B). Razón medida:
--   · la convención familia-genérica de s281 §2 se adjudicó para UNA familia; este
--     doc cubre TRES, así que no la cubre;
--   · con el compuesto de FAMILIAS ('NFS/VSN-LT/VSN-PLUS') ningún miembro casa el
--     model-filter ('nfs2' ⊄ 'nfs/vsnlt/vsnplus'), y este doc NO tiene entrada en
--     `doc_map.jsonl` (verificado: doc_map_ids=[]) → el Canal A del resolver
--     tampoco lo alcanzaría → quedaría igual de invisible que con 'unknown';
--   · con los miembros enumerados TODOS casan ('nfs2','vsn2lt','vsn2plus' ⊂ tag).
-- Si Alberto prefiere la coherencia de convención (opción A), hay que añadir
-- ADEMÁS los paraguas 'NFS' y 'VSN PLUS' + el doc_map de este fichero; solo
-- entonces A ≈ B en alcance.
--
-- UPDATE chunks_v2 SET product_model =
--        'NFS2/NFS4/NFS8/VSN2-LT/VSN4-LT/VSN8-LT/VSN12-LT/VSN2-PLUS/VSN4-PLUS/VSN8-PLUS/VSN12-PLUS'
-- --   OPCIÓN A (compuesto de familias):  SET product_model = 'NFS/VSN-LT/VSN-PLUS'
--  WHERE source_file = 'Finales-de-linea-de-las-centrales-convencionales'
--    AND product_model = 'unknown'
--  RETURNING id;  -- esperado: 1 fila
--
-- NOTA COLATERAL (no bloquea): el doc-level de este fichero es pm='NFS2-8' y
-- mfr='Morley' aunque el contenido mezcla NFS (Notifier) y VSN (Morley), y
-- language='de' con contenido en español. Son ejes T2/doc-level, fuera de esta lane.

-- ── #24 · No-puedo-conectarme-con-el-ordenador-a-la-central-ZX · 1 chunk ────
-- Alberto: cubre ZX2e/ZX5e/ZX2Se/ZX5Se = AMBAS familias → propone 'ZXe/ZXSe'.
--
-- RECOMENDACIÓN DE LA LANE: **SÍ, 'ZXe/ZXSe'** — es el compuesto de las DOS
-- etiquetas-familia que YA están vivas en la DB (verificado: ZXSe=88, ZXe=207),
-- ambos tokens casan el canal keyword ('zxe' y 'zxse' ⊂ 'zxe/zxse'), y los
-- MIEMBROS llegan por Canal A porque este doc SÍ tiene doc_map
-- (morley:zx2e/zx2se/zx5e/zx5se — verificado en el packet §6). Riesgo bajo.
--
-- UPDATE chunks_v2 SET product_model = 'ZXe/ZXSe'
--  WHERE source_file = 'No-puedo-conectarme-con-el-ordenador-a-la-central-ZX'
--    AND product_model = 'unknown'
--  RETURNING id;  -- esperado: 1 fila

-- ── #25 · RP1R-SUPRA-VSN-RP1R-PLUS2-Teclado-bloqueado · 1 chunk ─────────────
-- Alberto: RP1R-Supra y VSN-RP1R-PLUS2 son 2 productos DISTINTOS (mapa s78) →
-- compuesto.
--
-- RECOMENDACIÓN DE LA LANE: **'RP1r-Supra/VSN-RP1r-PLUS2'** (casing del catálogo
-- gobernado, 'RP1r' con r minúscula; el matching es case-insensitive). Ambos
-- cores casan el model-filter.
-- ⚠ CONFLICTO DE CATÁLOGO A ADJUDICAR APARTE (verificado en
-- `data/catalog/aliases.jsonl`): hoy existe el alias 'VSN-RP1r-PLUS2' →
-- notifier:rp1r-supra, es decir el catálogo los trata como el MISMO producto, lo
-- contrario de esta adjudicación. Además existe `unresolved:vsn-rp1r-2plus`
-- (candidate) como producto separado. Re-apuntar ese alias es una decisión de
-- identidad, NO la toca esta lane.
--
-- UPDATE chunks_v2 SET product_model = 'RP1r-Supra/VSN-RP1r-PLUS2'
--  WHERE source_file = 'RP1R-SUPRA-VSN-RP1R-PLUS2-Teclado-bloqueado'
--    AND product_model = 'unknown'
--  RETURNING id;  -- esperado: 1 fila


-- ════════════════════════════════════════════════════════════════════════════
-- §5 · OPCIONALES DECLARADOS (fuera de las 26 adjudicaciones) — COMENTADOS
-- ════════════════════════════════════════════════════════════════════════════

-- ── OPCIONAL-B · coherencia de marca del hermano LocatorPlus-EN ─────────────
-- Deriva de #7: el manual EN del MISMO producto se quedaría en 'LGM Products'.
-- UPDATE chunks_v2 SET manufacturer = 'Signaline'
--  WHERE source_file = 'LocatorPlus-EN-Installation-Manual-1.0'
--    AND manufacturer = 'LGM Products'
--  RETURNING id;  -- esperado: 19 filas
-- (si se aplica, añadir antes su source_file al respaldo de §0)

-- ── OPCIONAL-C · alinear doc-level con la adjudicación de chunk ─────────────
-- Esta lane es chunk-level. `documents.product_model` sigue con las etiquetas
-- viejas en varias fichas (p.ej. 'B501AP' en #12, 'D700' en #16, 'FS2-1' en #1,
-- 'NFS2-8' en #23, 'Notifier Strobe' en #14). Alinearlo es coherente pero NO fue
-- adjudicado y toca la tabla gobernada `documents` → decisión aparte.


-- ════════════════════════════════════════════════════════════════════════════
-- §6 · GATE DE EVAL — OBLIGATORIO antes de dar el tramo por bueno
-- ════════════════════════════════════════════════════════════════════════════
-- Patrón cat022/s281 §2.5. El re-tag redistribuye los pools de retrieval/rerank
-- de cualquier QID cuya query nombre uno de los modelos ahora etiquetados.
--
-- BARRIDO VERIFICADO de `evals/gold_answers_v1.yaml` contra los 26 source_file:
--   · `HLSI-MA-025` aparece 1 vez, en el bloque de fuentes de **cat009**
--     («¿Qué resistencia de fin de línea (EOL) … de la central convencional NFS
--     Supra?»). Las fichas #15 y #20 etiquetan justo los docs NFS Supra →
--     **cat009 ES el gold en riesgo de este tramo**.
--   · `MIE-MI-530` aparece 15 veces (hp009/hp018) — pero esa migración (ZXe) YA
--     está aplicada en la DB, así que su gate corresponde al estado actual, no a
--     este paquete. Se mantiene en el set por ser el control histórico del tramo.
--   · Ningún otro de los 26 source_file aparece en los golds.
--
-- PLAN (antes de dar por bueno; el re-tag es reversible por §7):
--   python scripts/test_bot_vs_gold.py    # dirigido a: cat009 (afectado) +
--                                          #  hp009/hp018 (control ZX) +
--                                          #  hp006/hp010 (control no-tocado)
-- Criterio de aceptación: cat009 no empeora, hp018 se mantiene PASS, hp009 no
-- empeora, y los controles no se mueven. Baseline vigente: v3 (s284,
-- `evals/bot_vs_gold_39_baseline_c1v4_v3judgefull_s284.yaml`) — 16 PASS/20
-- PARCIAL/3 FALLO. Correr con PARIDAD COMPLETA DE FLAGS (DEC-157).


-- ════════════════════════════════════════════════════════════════════════════
-- §7 · ROLLBACK EXACTO (desde la pre-imagen de §0)
-- ════════════════════════════════════════════════════════════════════════════
-- Total (product_model + manufacturer, las 26 fichas):
-- UPDATE chunks_v2 c
--    SET product_model = b.product_model_prev,
--        manufacturer  = b.manufacturer_prev
--   FROM _s285_t3_backup b
--  WHERE c.id = b.id
--    AND (c.product_model IS DISTINCT FROM b.product_model_prev
--         OR c.manufacturer IS DISTINCT FROM b.manufacturer_prev);

-- Parcial (una sola ficha):
-- UPDATE chunks_v2 c
--    SET product_model = b.product_model_prev, manufacturer = b.manufacturer_prev
--   FROM _s285_t3_backup b
--  WHERE c.id = b.id AND b.source_file = '<source_file>';

-- Verificación post-rollback (debe volver a 227 / 26):
-- SELECT count(*) FROM chunks_v2 c JOIN _s285_t3_backup b ON b.id = c.id
--  WHERE c.product_model = 'unknown';   -- esperado: 227

-- Limpieza (SOLO tras cerrar el tramo y con el gate verde):
-- DROP TABLE _s285_t3_backup;
