# s316 v2 — Instrumento de transporte: la síntesis que el dúo prescribió

> El v1 (`s316_instrumento_mt_transporte_propuesta_v1.md`) fue **NO-SÓLIDO ×2** (Sol +
> sub-agente Opus). Este v2 NO es un diseño mío sometido a ronda nueva: es la
> **prescripción convergente de ambos revisores**, verificada claim a claim (regla C), y
> se construye directamente. Revisar a los revisores su propia prescripción sería ritual.

## Qué mató al v1 (todo verificado ejecutando/leyendo, no aceptado de palabra)

1. **Censo de rutas falso en tres formas**: `coverage_append`/`already_served` son
   `satisfaction_route` de la lane document-local (mi grep casó `route=` dentro de
   `satisfaction_route=`); `rag` es el DEFAULT de la firma (`logging_db.py:142`), invisible
   a un AST de call-sites; y F1 emite `clarify`/`decline` con un `IfExp`
   (`telegram_bot.py:1208-1210`) — mi parser habría reventado contra el código de hoy.
2. **Ya existe taxonomía canónica**: el CHECK `query_logs_route_check` (migración s301).
   Enumerar por AST era reinventar mal un contrato que vive en la DB.
3. **El unit correcto es la RAMA TERMINAL, no la ruta**: 7 de los 13 `return` de
   `handle_message` responden **sin** `log_query` — una puerta por rutas es ciega a la
   mitad de las ramas, y esa clase de rama ES #70.
4. **Rojo no atribuible**: `_process_query:1509-1538` traga toda excepción y loggea
   `route='rag'` — un doble roto daría el mismo rojo que el bug. Hacen falta controles
   causales y aserción anti-rama-de-error.
5. **Sobre-ingeniería**: `test_f1_activation_wiring.py:38-116` ya tiene el doble de
   `Update`, `user_data` persistido, flags F1 congelados y aserciones sobre
   `mt_working_state`. El delta es conducir `handle_message`. YAML+censo-AST no son
   prerrequisitos probados (y BP aquí incluye «sin sobre-ingeniería», CLAUDE.md).
6. **Control de compatibilidad vacuo con Hochiki** (marca NO servida: `manufacturer_in_db`
   la rechaza en `:912` antes de llegar a la política) → el control usa marca SERVIDA.
7. Refutación en sentido contrario (regla C a favor): el menor de Opus sobre «`route`
   podría ser NULL en la fila orgánica» es falso — esta sesión leí
   `route='catalog_shortcut'` de `query_logs` directamente.

## El instrumento (lo que se construye)

`tests/test_s316_transport_state_instrument.py`, extendiendo el patrón de
`test_f1_activation_wiring`:

| Pieza | Qué es | Estado esperado HOY |
|---|---|---|
| **Testigo A→B→C** | El fallo orgánico por `handle_message` real: NC-PF2 → «pasemos a productos Morley…» (catalog_shortcut) → follow-up. Asserta que la generación del turno C NO ve `contexto: NC-PF2` | **ROJO** → `xfail(strict=True)`: documenta #70; cuando el fix aterrice, el XPASS obliga a quitar el marcador |
| **Control causal** | Mismo A→B→C con `mt_working_state` limpiado a mano tras B | **VERDE**: prueba que el rojo del testigo es el bug, no el doble |
| **Control de no-regresión** | A (NC-PF2) → «¿es compatible con Morley?» (marca servida, sin intención de switch): el carry-forward DEBE conservarse | **VERDE** hoy y tras cualquier fix |
| **Censo de ramas terminales** | AST sobre los `Return` de `handle_message`/`handle_voice`: recuento congelado. Rama nueva ⇒ rojo hasta actualizar el censo CONSCIENTEMENTE | **VERDE** (censo casa); la parte estructural sin la fragilidad del censo por rutas |

Reglas del doble (de los hallazgos): los deciders de DB (`manufacturer_in_db`,
`_inventario_fabricante`, `_handle_catalog`) se stubean como **precondiciones declaradas**
calibradas a producción (Morley SÍ servida) — el responder es I/O, el router no se toca;
flags F1 congelados ANTES del import (patrón `:92-93`); `has_consent` → True;
`reply_to_message=None`; aserción anti-rama-de-error en todos los casos (la respuesta no
puede ser el fallback de excepción); `log_query` grabado para afirmar la ruta del turno B.

## Gaps que HEREDA (declarados, no resueltos)

- `user_data` de PTB es por-USUARIO, no por-conversación (hallazgo Opus): el doble replica
  la semántica real; no inventa aislamiento por chat.
- Sin control de reloj (`datetime.now` con import local): los casos de ventana/expiración
  quedan fuera; los tres turnos corren dentro de la ventana. Limitación declarada.
- El testigo reproduce el **precondicionante de estado**, no el daño completo (la
  generación está stubeada). Es lo que un instrumento $0 puede afirmar.
- Mide enrutado y estado, no calidad. El eje MT de Fase 2 sigue siendo otro.
