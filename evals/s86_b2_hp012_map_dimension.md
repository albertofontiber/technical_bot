# s86·B2 — hp012 (AM2020/AFP1010): ¿el activo de identidad limpia el pool coupled?

Familia: hp012 · query_model = AM2020 / AFP1010 · fact-miss = "2 lazos / 396" (fact#2, bucket RETRIEVAL, in_pool=false).
Manuales correctos del fact: **MFDT280** (pm DB "AM2020 y AFP1010" = combinado) y **MPDT280** (pm DB "MPDT-280").

## Pool hoy (50 chunks, pinneados)
- correct-manual-src (en manual_pin): 19  ·  wrong-family-src: **31/50** (confirma la cifra del brief).
- Los dos GRANDES flooders:
  - **15037SP** = 11 chunks, DB pm="AM-2020"  → map: `primary-of ['lcd80']` (canonical LCD-80). family_scope s83 vacío.
  - **MIDT340** = 8 chunks, DB pm="AFP1010"    → map: `primary-of` familia audio/telefonía (AA100/FFT7/AMG…). s83 family_scope = "Sistema de Megafonía y Telefonía PARA centrales AM2020/AFP1010" (accesorio, no la central).
- Ninguno de los dos aparece bajo `am2020` ni `afp1010` en NINGÚN rol del índice.

## Map-filter (primary-of am2020 OR afp1010) sobre los 50
- DROP 19 = **15037SP(11) + MIDT340(8)** → los 19 son wrong-family. **0 correctos caídos.**
- KEEP 31 = 19 correctos + 12 "wrong" residuales.
- Los 12 residuales (MADT283/284/285, MPDT281, BTDT032, MADT280/281, MADT285_01) tienen s83 family_scope = "AM2020/AFP1010" o "AM2020": son sub-manuales GENUINOS de la MISMA familia (config/mantenimiento/boletín/operación), no wrong-family real. El DEF.yaml los marca "wrong" solo por no ser el combinado que porta el fact.
- Net: **wrong-family REAL dropeado = 19/31**; el residuo de 12 es intra-familia, no ruido de otra central.

## Map MÁS limpio que DB en AMBAS direcciones
1. DROP: DB taggea 15037SP="AM-2020" y MIDT340="AFP1010" → **un filtro por pm-DB NO puede excluirlos**. El map sí (primary=LCD-80 / audio).
2. INCLUDE: value-chunk `5730afb3` (src MPDT280) tiene DB pm="**MPDT-280**" (código de manual como si fuera producto). Un filtro pm-DB="AM2020" lo PERDERÍA; el map lista MPDT280 `primary-of am2020/afp1010` → lo INCLUYE.

## Manual combinado — SÍ manejado
`am2020` y `afp1010` listan AMBOS MFDT280 y MPDT280 como PRIMARY (atribución a los dos productos). El doc combinado + el pm compuesto quedan correctamente bajo las dos claves. No hay pérdida por el "y"/"/" del pm.

## Residual / caveats
- El filtro NO limpia el residuo intra-familia de 12 (mismo AM2020/AFP1010): dentro de la familia el map no separa "combinado-con-el-fact" de "sub-manual". Eso queda al retrieval/rerank.
- **No hay score/rank en los pins** → probado que el map DESCONGESTIONA (libera 19 slots de 50) y que el value-chunk pertenece a la familia; NO probado que el value-chunk suba al top-K tras filtrar (podría ser cosine sub-suelo, clase s86 fine-grained). Dimensiona el cuello de pool-crowding, no el de ranking.
