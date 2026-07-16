# S117 M2 — guard replay-only v2.6

El prereg v2.6 hereda el contrato lingüístico v2.5 pero lo hace ejecutable de
forma fail-closed:

1. exige `--replay`; omitirlo aborta antes de preflight/carga de credenciales;
2. rechaza siempre `--env-file`;
3. exige que `--snapshot`, resuelto, sea exactamente el path congelado;
4. el preflight verifica el SHA-256 gzip del path congelado;
5. tras leer el fichero consumido, el analyzer exige que tanto su SHA gzip como
   su SHA JSONL canónico coincidan con el prereg.

Estos guards aplican únicamente cuando existe `seeded_replay_gate`; un prereg
histórico explícito conserva su semántica histórica. Los tests deben probar
rechazo de captura, credenciales, path alternativo y recibos gzip/JSONL
incorrectos. No se autoriza ninguna nueva lectura remota.
