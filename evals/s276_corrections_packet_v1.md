# S276 — paquete de correcciones a atacar

Estado solicitado: revisión adversarial de las correcciones posteriores al primer dúo. No concede
permiso de runtime/schema/deploy.

## Cambios bajo revisión

1. `scripts/adversarial_review_fable.py` ya no obliga a repetir un run completo cuando el proveedor
   termina `end_turn` con bloque `text` vacío después de usar tools. Hace como máximo un recovery
   dentro del mismo run, fuerza tools-off, conserva la respuesta vacía en el provider trace y exige
   un cierre final no vacío. El validator físico sólo debe aceptar:
   `tool_use* → [como máximo un end_turn vacío inmediatamente penúltimo] → end_turn final`.
2. `max_tokens`, model mismatch, presupuesto insuficiente, segundo final vacío y tool request
   durante recovery siguen fail-closed. No hay retry automático de truncados.
3. Tests cubren éxito, segundo vacío, receipt físico válido, secuencias múltiples/no vacías y las
   invariantes anteriores.
4. El closeout seed-278 rebaja 67/67 a autoconsistencia del parser, etiqueta los boundary controls
   como sintéticos y declara el freeze incompleto. El resultado sigue `NO_GO_OFFLINE_SCREEN`.
5. El blueprint conversacional separa verifier de repair, reconoce repair como segundo writer,
   añade lifecycle RGPD, leases/order/CAS/outbox/receipts y no promete exactly-once externo.

## Claims que deben verificarse contra código/artefactos

- El recovery no puede ejecutar tools ni más de una vez.
- El receipt no puede seleccionar texto de un response arbitrario, omitir el vacío ni aceptar un
  `end_turn` intermedio no vacío o fuera de posición.
- Usage, IDs, modelos, stop reasons, tool trace y texto normalizado siguen ligados al trace físico.
- La secuencia de mensajes enviada al API es válida y no rompe el presupuesto acumulado.
- Los tests no sólo prueban el helper equivocado o un mock que el path real no usa.
- Ningún wording de cierre convierte hashes post-run en prueba de cronología del freeze.
- La arquitectura sigue siendo `DIRECTIONAL_BLUEPRINT_NO_BUILD_AUTHORIZATION`; no mezcla
  idempotencia de ingress, duplicación de cómputo y entrega externa.

## Resultado esperado

Encontrar defects reales o declarar sólido. Cualquier finding debe anclar línea/claim y separar:
bug del runner, debilidad del test, framing del screen o gap conceptual del blueprint. No se pide
reabrir seed-278 ni proponer otra A/B.
