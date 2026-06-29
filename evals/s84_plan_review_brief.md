# Revisión adversarial — PLAN de ejecución revisado de F (re-medir L-i para base limpia) — s84, zona de dolor retrieval

## Trayectoria (por qué se re-revisa — leedlo, es el contexto)
- **Ronda 13 (vosotros):** cazasteis que Claude RE-LITIGABA — proponía "vectorial ancho / quitar el filtro de categoría" como BP fresco SIN leer que = lever **L-i (DEC-040)** ya A/B-**ROLLBACKEADO** (Δ_net=0, flipeó frontera) + variante **MERGE+L-i′ (DEC-050)** = **gate-0 NO-GO** post-ef=120. Correcto. El cross-model dijo: *"si se re-propone, debe ser 'reabrir un lever rollbackeado con DISEÑO NUEVO', no 'aplicar el principio'."*
- **DESPUÉS Alberto hizo pushback** (y Claude concedió que su "settled, no tocar" sobre-corrigió): el filtro está roto y es **factor LIMITANTE** (cuando se arregle el ranking, los chunks buenos fluirán — DEC-040 mismo nombra el lever de ranking como el siguiente paso); y propuso **QUITARLO AHORA para SENTAR UNA BASE LIMPIA** sobre la que medir la mejora de identidad sin el confound del filtro roto.
- → El plan ahora **re-abre L-i**. **Esto es el "diseño nuevo/justificación" que el cross-model dijo que haría falta — pero NO lo habéis vetado. Eso es lo que se revisa ahora.**

## El PLAN revisado (a ATACAR)
0. commit del activo de identidad (cerrado, dúo-validado r10-r12).
1. **Base limpia: RE-MEDIR L-i** (vectorial ancho, sin filtro de categoría) en el sustrato ACTUAL (ef=120 + config hoy; código en rama `s59-lever-code-ROLLBACKED` + instrumentos del A/B existen). **Justificación nueva:** (a) re-BASAR ≠ shippear un lever de calidad → aceptar el net-zero a cambio de la corrección arquitectónica + medición limpia; (b) el sustrato cambió desde s59 (bias #35: no heredar la medida); (c) medir identidad (Fase 2) contra el vectorial-ancho-CORRECTO evita el confound del filtro roto. Gate dúo + Alberto.
2. Consumo de identidad modelo/familia (índice inverso producto→docs + resolución) medido contra la base de (1). **E (DB-apply) gateado por que mida ganancia.**
3. (Paralelo) canonicalizar la categoría free-text del activo → arreglar rutas de catálogo (`_handle_catalog`/`available_models`, rotas hoy por la columna muerta).
4. (Después) ranking-robusto (DEC-041) + categoría como boost soft (path no-model, TECH_DEBT #44).
+ QA en paralelo: muestra de acuerdos de los 985.

## Lo que pido (bite concreto, anclado en DEC-040/050)
1. **¿La justificación de re-abrir L-i es SÓLIDA, o es re-litigar disfrazado?** (a) ¿"re-basar aceptando net-zero" tiene sentido, o solo importa la perturbación de frontera a la nueva base (contaminándola)? (b) **¿El argumento "sustrato cambió" se sostiene, DADO que DEC-050 (s68) YA re-midió post-ef=120 → NO-GO?** ¿Qué cambió desde DEC-050 que justifique re-medir L-i (el activo de identidad NO arregla el ranking, que fue el bloqueante)? (c) ¿net-zero con flips de gold-de-ruido es una base LEGÍTIMA para medir, o envenena las mediciones futuras?
2. **¿La SECUENCIA es BP?** base-limpia(1) → identidad(2) → catálogo(3) → ranking(4). **¿O el lever de RANKING —el bloqueante REAL del rollback— debería ir ANTES de re-medir L-i?** (sin ranking robusto, L-i sigue reshuffleando la frontera).
3. **¿Hay un confound al revés** — re-basar con L-i AHORA podría OCULTAR o INFLAR la ganancia de identidad (Fase 2)? ¿Cómo aislar el efecto de L-i del de identidad?
4. ¿Algo que Claude (3 fallos en este hilo: 2 código + 1 re-litigar) siga sin ver?

Distinguid RE-LITIGAR (mismo experimento + misma justificación) de RE-ABRIR-LEGÍTIMO (propósito/sustrato nuevo). Verificad contra DEC-040/050 (regla C). Cross-model INNEGOCIABLE: autor y sub-agente ambos Opus.
