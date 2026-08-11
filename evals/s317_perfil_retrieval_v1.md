# s317 — Perfil de retrieve_chunks (rapidez fase 2) — resultado crudo

Corrida local, ruta harness, DB real, 2026-08-12. FRÍA 53,5 s (36 chunks) ·
CALIENTE 19,0 s (14 chunks; cProfile sobre esta).

## Atribución (caliente, 19,0 s)

| Qué | Coste | Detalle |
|---|---|---|
| 14× construcción de httpx.Client | **7,25 s** | `create_ssl_context`→`load_verify_locations` = 7,24 s (leer el bundle CA del disco 14 veces, ~0,52 s/vez) |
| 14× conexión TCP+TLS | **~3,4 s** | `_connect` 3,41 s — cada request paga handshake porque el cliente muere tras cada llamada |
| Espera de respuestas (RPC + payload) | ~8,2 s | `_ssl.read` 8,23 s — el único coste "legítimo" (ejecución en Supabase + transferencia) |

14 requests HTTP en UNA llamada: content_search ×3 (8,3 s cum) ·
_rank_window_by_authority ×3 (3,4 s) · vector_search (2,9 s) ·
_diversify_by_source_file (5,7 s cum, anidados) · resto.

## Conclusión

**Rapidez fase 2 ≡ TECH_DEBT #72** (cliente HTTP común): un cliente httpx
compartido a nivel proceso (un solo SSL context, pool con keep-alive) elimina
~10 s de los 19 s calientes y más en frío. Residual esperado tras el fix:
~6-9 s (RPCs reales) — atacable después en paralelo (canales secuenciales).

El embedding (Voyage) NO es el gordo. La secuencialidad de canales es el
segundo lever, DESPUÉS del cliente común.
