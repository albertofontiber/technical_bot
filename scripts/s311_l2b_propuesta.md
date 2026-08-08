# s311/L2b — Propuesta a atacar: registro declarativo de flags (rama claude/s311-l2b-flags)

## OBJETIVO + MÉTRICA
Blueprint §4-L2b (RECORTADO; diseño dúo-revisado en s300): src/flags.py = REGISTRO de las
87 flags que src/ lee del entorno (censo v4: getenv directo/indirecto, environ[.get],
_strict_on_off ambas firmas, _mp_flag, mapping.get-indirecto) + snapshot() sin secretos +
test de completitud NOMINAL bidireccional + pin de DEMO_FLAGS por nombre. CERO lectores
migrados (0 regen de sellos). Métrica: ningún lever; flags.py es módulo nuevo que nadie de
src/ importa. Suite 3635 passed.

## HALLAZGOS PROPIOS YA DECLARADOS (verifícalos, no los re-descubras)
- Fantasma DIVERSIFY_TIEBREAK en DEMO_FLAGS (lever s97 NO-GO nunca mergeado) — declarado
  en el test con su historia; NO se borra del harness (identidad de la config).
- 2 divergencias de defaults entre lectores, DECLARADAS en sus entradas
  (IDENTITY_RESOLVE_POLICY "" vs None; ANTHROPIC_API_KEY "" vs None).
- 2 bugs de contaminación de entorno cazados y arreglados: import de factlevel fija
  DEMO_FLAGS en os.environ (envenenaba s69) → subproceso; y el env de la suite llega
  tocado (envenenaba al subproceso) → entorno LIMPIO explícito.
- Excepción declarada de la heurística de sensibles: MP_DISTINCTIVE_TOKEN (token de
  EVIDENCIA del contrato must-preserve, no credencial).

## CLAIMS A ATACAR
C1 registro FIEL al árbol (muestrea ≥10 entradas, incluidas divergencias y vías raras).
C2 completitud sin escotillas: ¿alguna forma de lectura de entorno que los 6 patrones no
cubran, y el test no cazaría? C3 snapshot() sin fuga posible (¿default_fuente textual con
secreto? ¿sensible sin marcar que la heurística por-partes no vea?). C4 el fantasma es
inocuo para el assessment. C5 aislamiento completo (¿otro camino de contaminación?).
C6 matriz del contrato intacta (flags = raiz, importa solo os).

## PREGUNTAS DURAS
¿Duplica clasificación que release_config s277 ya tiene y pueden DIVERGIR en silencio —
falta un test de coherencia entre ambos o está justificado que no? ¿El test de completitud
es frágil ante refactors legítimos (renombrar _strict_on_off)? ¿snapshot() con el env real
de Railway expondría algo vía default_fuente?
