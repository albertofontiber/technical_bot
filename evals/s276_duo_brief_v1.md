# S276 — brief para review adversarial

## Decisiones a atacar

1. El screen offline seed-278 se cierra `NO_GO_OFFLINE_SCREEN`: la forma mecánica pasa, pero el
   mínimo preregistrado de fabricantes falla (2 < 3) y la inspección posterior evidencia fuerte
   dominancia visual/UI. No se construye runtime ni se paga A/B.
2. Se propone como norte —sin autorización de build— un orquestador transport-neutral y acotado:
   event log/estado durable primero con paridad single-hop; rewrite sólo en follow-ups; máximo
   2 hops por defecto/3 hard cap; un writer final; evidence/claim+verifier únicamente tras cohorte
   fresca y control contemporáneo.
3. `146/154` y un eventual `151/154` se tratan como hitos internos, no como una tasa productiva
   universal; 100 % no se presenta como norma de RAG.

## Ataques requeridos

- Verifica en código/artefactos si el freeze ocurrió realmente antes del GET y si la población,
  exclusiones, métodos HTTP, gates, hashes, NO-GO y controles se calculan como se afirma.
- Busca leakage target, selección condicionada por outcomes, hashes no revalidados, métricas
  tautológicas, prevalencia sobreafirmada, falsos positivos semánticos disfrazados de estructurales
  y cualquier camino por el que un resultado NO-GO pudiera reinterpretarse como permiso.
- Comprueba si la arquitectura reabre con otro nombre S206, S216, S235, S248, S260 o el agentic
  deep lookup; cita su métrica correcta y el objetivo sobre el que fue medida.
- Ataca especialmente memoria/consentimiento/RGPD, `service_role` frente a RLS, idempotencia,
  concurrencia por conversación, event loop síncrono, provenance de resúmenes, contaminación por
  respuestas anteriores, límites de hops, coste y observabilidad.
- Señala afirmaciones estadísticas o de literatura demasiado fuertes. El blueprint debe distinguir
  evidencia local, evidencia externa e inferencia de ingeniería.
- Devuelve hallazgos accionables anclados. `SÓLIDO` es una salida válida si no hay defectos
  materiales; no inventes rituales para justificar el review.

## Límites

- No se solicita diseño runtime detallado ni DDL en S276.
- No se reabre seed-278, no se ajusta el detector con sus outputs y no existe target probe #5.
- Cualquier issue del screen se corrige sólo si preserva honestamente el freeze; si exige cambiar
  mecanismo/población/gate, el resultado sigue NO-GO y la nueva hipótesis requiere otra semilla.
