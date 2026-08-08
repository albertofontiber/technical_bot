# s313/L2c — Propuesta a atacar: split del doble-inquilino (rama claude/s313-l2c-split)

## OBJETIVO + MÉTRICA
Blueprint §4-L2c: `rerank_pool_coverage` (735 líneas, doble-inquilino) partido en
`pool_selection` (motor) + `obligation_warning` (reserva VIVA que sirve en producción
bajo coverage_c1_v4) + residual (lane VETADA + shim declarado mínimo). E3c retirada
(must_preserve migra a los módulos nuevos): excepciones 5→4, cuarentena 3→2. Métrica:
**lógica BYTE-IDÉNTICA (solo bloques movidos + imports)**; la reserva viva debe producir
EXACTAMENTE lo mismo; ningún lever. Suite 3636 passed. Sello: +2 entradas manifest
(exigidas fail-closed por el gate); el residual se queda (unreachable=[]).

## CLAIMS A ATACAR (C1 es el central)
- C1 BYTE-IDENTIDAD: compara símbolo a símbolo origin/main:rerank_pool_coverage.py
  contra la unión de los 3 módulos. ¿Cuerpo cambiado? ¿Símbolo perdido? ¿DUPLICADO
  (dos definiciones vivas)? ¿Side-effects de orden de import?
- C2 la reserva VIVA indistinguible: ¿select_obligation_warning_reserve usaba algo vía
  el namespace del módulo viejo (global monkeypatcheable, flag module-level) que cambie
  al vivir en otro módulo?
- C3 seam de tests: los 5 monkeypatch de rerank_pool_coverage.resolve_query siguen
  mordiendo; ¿algún OTRO patch sobre el módulo viejo quedó apuntando a un módulo que ya
  no usa el símbolo (test verde midiendo NADA)?
- C4 sello: ¿+2 entradas basta? ¿el pipe_sha del assessment cambia y falta smoke+fila
  (L1 los pagó)?
- C5 contrato: E3c limpia, censo 117, ¿el trigger «muerte de la lane vetada» es
  correcto o vago?
- C6 registro de flags regenerado tras el split: ¿OBLIGATION_RESERVE_ORDERED apunta ya
  a obligation_warning.py?

## PREGUNTAS DURAS
¿must_preserve:2493 conserva la semántica de fallo del import? ¿El shim re-exporta el
MÍNIMO exacto? ¿Los 8 nombres de E3b tienen hogar correcto? ¿Docstrings nuevos afirman
algo no verificado?
