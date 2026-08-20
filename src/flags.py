"""src/flags.py — REGISTRO declarativo de la configuración por entorno (L2b, s311).

Qué ES: el censo ejecutable de las 97 flags que `src/` lee del entorno — censo v5,
fuente UNICA en `tests/_censo_flags.py` (8 vias, ambas comillas, profile-owned por
import del constante, y flags data-driven de los YAML de fabricantes), con default (como TEXTO fuente — el lector real
es quien lo resuelve), vía y lectores por flag. Generado del árbol y VERIFICADO contra
el árbol por `tests/test_s311_flags_registry.py`: un `getenv` nuevo sin registrar pone
la suite en rojo.

Qué NO es (alcance honesto, del blueprint §4-L2b tras su dúo):
  · NO migra lectores — los sellados siguen leyendo como leen (0 regen de sellos); la
    migración al accessor es oportunista, cuando otro lote toque su fichero.
  · La completitud es NOMINAL: garantiza que no hay call-site TEXTUAL sin registrar,
    no equivalencia semántica de parsing entre lectores no migrados.
  · El pin de `DEMO_FLAGS` detecta NOMBRES no registrados (pins fantasma), no valores.
  · Una DIVERGENCIA de defaults entre lectores se declara VISIBLE en su entrada, no se
    corrige a ciegas (hoy exactamente DOS, ambas con lados falsy y adjudicación
    pendiente no-urgente: `IDENTITY_RESOLVE_POLICY` ("" vs None) y
    `ANTHROPIC_API_KEY` ("" en config vs None en otro lector).

`snapshot()` sirve el estado ACTUAL sin secretos: las flags `sensible` reportan solo
presente/ausente. Es el insumo para comparar harness↔Railway sin exponer credenciales.
"""
from __future__ import annotations

import os

REGISTRO: dict[str, dict] = {
    "ANSWER_OBLIGATION_PLANNER": {
        "default_fuente": '"off"',
        "via": ['getenv'],
        "lectores": ('src/rag/answer_planner.py',),
    },
    "ANTHROPIC_API_KEY": {
        "default_fuente": '""',
        "via": ['environ.get', 'getenv'],
        "lectores": ('src/config.py', 'src/rag/must_preserve.py'),
        "sensible": True,
        "divergencia": ['""', 'None'],  # VISIBLE a proposito (L2b: el pin detecta, no corrige)
    },
    "ANTI_DIAGRAM_INVENTION": {
        "default_fuente": '"on"',
        "via": ['getenv'],
        "lectores": ('src/rag/generator.py',),
    },
    # s324e — control de acceso al piloto. Las TRES nacen en `bot/access.py`.
    # `BOT_ALLOWLIST` es el interruptor maestro de la puerta y nace OFF porque
    # `main` auto-despliega mientras las migraciones las aplica Alberto a mano:
    # encendida por defecto, el commit que la trae cerraria el bot antes de que
    # exista la tabla. Es ademas el kill-switch (vuelta al bot de hoy, sin deploy).
    "BOT_ALLOWLIST": {
        "default_fuente": '"off"',
        "via": ['getenv'],
        "lectores": ('src/bot/access.py',),
    },
    # Ids SIEMPRE autorizados, sin pasar por base ni cache. Es la respuesta
    # explicita y auditable a «Alberto no puede quedarse fuera al desplegar», en
    # lugar de un `if user_id == …` en el codigo. NO es sensible: un id de
    # Telegram no es una credencial (no abre nada por si mismo) y verlo en un
    # snapshot es justamente lo que permite auditar quien tiene el atajo.
    "BOT_ALLOWLIST_BOOTSTRAP": {
        "default_fuente": '""',
        "via": ['getenv'],
        "lectores": ('src/bot/access.py',),
    },
    # Tope de mensajes por persona y dia (0 = sin tope). Barrera de GASTO del
    # piloto; el contador vive en memoria y un redeploy lo reinicia (declarado).
    "BOT_DAILY_LIMIT": {
        "default_fuente": '"30"',
        "via": ['getenv'],
        "lectores": ('src/bot/access.py',),
    },
    "BOT_ERROR_LOGGING": {
        "default_fuente": '"off"',
        "via": ['getenv'],
        "lectores": ('src/bot/telegram_bot.py',),
    },
    # s324e: kill-switch del MENSAJE de error al tecnico. Default "on" — de las
    # pocas del registro que nacen encendidas, y a proposito: lo que sustituye
    # es el SILENCIO de hoy, asi que un default off dejaria el mecanismo inerte
    # justo donde hace falta. Apagarlo devuelve la conducta actual sin deploy.
    "BOT_ERROR_REPLY": {
        "default_fuente": '"on"',
        "via": ['getenv'],
        "lectores": ('src/bot/telegram_bot.py',),
    },
    "BOT_VERSION": {
        "default_fuente": '""',
        "via": ['getenv'],
        "lectores": ('src/version.py',),
    },
    "CANONICAL_HYQ_COVERAGE": {
        "default_fuente": '"off"',
        "via": ['strict_on_off'],
        "lectores": ('src/config.py',),
    },
    # s326: corrida periódica del clasificador de preguntas (query_clasificacion)
    # en la JobQueue del worker. Default off = conducta idéntica (no se programa
    # nada); el batch manual (backfill/re-taxonomización) vive en scripts/ y no
    # depende de este flag.
    "CLASIFICADOR_PREGUNTAS": {
        "default_fuente": '"off"',
        "via": ['strict_on_off'],
        "lectores": ('src/config.py',),
    },
    "CHUNKS_TABLE": {
        "default_fuente": '"chunks_v2"',
        "via": ['getenv'],
        "lectores": ('src/config.py', 'src/rag/catalog_resolver.py', 'src/rag/deep_lookup.py'),
    },
    "COMPATIBILITY_BUNDLE_COVERAGE": {
        "default_fuente": '"off"',
        "via": ['strict_on_off'],
        "lectores": ('src/config.py',),
    },
    "CONVERSATION_POLICY": {
        "default_fuente": '"impl"',
        "via": ['getenv'],
        "lectores": ('src/orchestrator/conversation_policy_impl.py',),
    },
    "CONVO_MAINTENANCE": {
        "default_fuente": '"off"',
        "via": ['strict_on_off'],
        "lectores": ('src/config.py',),
    },
    "CONVO_SHADOW": {
        "default_fuente": '"off"',
        "via": ['strict_on_off'],
        "lectores": ('src/config.py',),
    },
    "COVERAGE_MANDATORY_CALLOUT": {
        "default_fuente": '"off"',
        "via": ['profile-owned-loop', 'strict_on_off'],
        "lectores": ('src/rag/post_rerank_coverage.py', 'src/release_profiles.py'),
    },
    "COVERAGE_RELEASE_PROFILE": {
        "default_fuente": 'None',
        "via": ['mapping.get-indirecto'],
        "lectores": ('src/release_profiles.py',),
    },
    "DEDUP_REFERENCE_NAVIGATION": {
        "default_fuente": '"off"',
        "via": ['strict_on_off'],
        "lectores": ('src/config.py',),
    },
    "DOCUMENT_LOCAL_COVERAGE": {
        "default_fuente": '"off"',
        "via": ['profile-owned-loop'],
        "lectores": ('src/release_profiles.py',),
    },
    "DOCUMENT_LOCAL_SELECTION_V2": {
        "default_fuente": '"off"',
        "via": ['profile-owned-loop', 'strict_on_off'],
        "lectores": ('src/rag/document_local_coverage.py', 'src/rag/post_rerank_coverage.py', 'src/release_profiles.py'),
    },
    "EMBED_CACHE_PATH": {
        "default_fuente": 'None',
        "via": ['getenv'],
        "lectores": ('src/ingestion/embedder.py',),
    },
    "EMBED_MODEL": {
        "default_fuente": '"voyage-4-large"',
        "via": ['getenv'],
        "lectores": ('src/reingest/embed.py',),
    },
    "EMBED_PROVIDER": {
        "default_fuente": '"voyage"',
        "via": ['getenv'],
        "lectores": ('src/reingest/embed.py',),
    },
    "ENUNCIADOS_MULTIVECTOR": {
        "default_fuente": '"on"',
        "via": ['getenv'],
        "lectores": ('src/rag/retriever.py',),
    },
    "ENUNCIADOS_QUOTA_FUSION": {
        "default_fuente": '"off"',
        "via": ['getenv'],
        "lectores": ('src/rag/retriever.py',),
    },
    "EVIDENCE_CONTRACT": {
        "default_fuente": '"off"',
        "via": ['profile-owned-loop', 'strict_on_off'],
        "lectores": ('src/rag/generator.py', 'src/release_profiles.py'),
    },
    "EVIDENCE_DERIVATION_OVERLAY": {
        "default_fuente": '"off"',
        "via": ['strict_on_off'],
        "lectores": ('src/config.py',),
    },
    "EXTRACTION_CACHE_DIR": {
        "default_fuente": 'tempfile.gettempdir() / "technical_bot_extraction"',
        "via": ['getenv'],
        # s325b: donde se cachean las extracciones descargadas del bucket.
        # No es un flag de conducta: mueve un directorio de trabajo (util en
        # tests y en un VM con disco acotado). La cache se indexa por sha, asi
        # que cambiarla no puede servir contenido viejo.
        "lectores": ('src/extraction_store.py',),
    },
    "FACET_COMPLEMENT_FALLBACK": {
        "default_fuente": '"off"',
        "via": ['strict_on_off'],
        "lectores": ('src/rag/post_rerank_coverage.py',),
    },
    "F1_MENTION_PRECEDENCE": {
        # (s331 §3.C.1) Precedencia de mención no-resuelta + gramática de confirmación
        # en la política F1. Default off = byte-idéntico; no exige F1_RESOLVE_GOVERNED
        # (G1c mide C-solo).
        "default_fuente": '""',
        "via": ['getenv'],
        "lectores": ('src/orchestrator/conversation_policy_impl.py',),
    },
    "F1_RESOLVE_GOVERNED": {
        # (s331 §3.A) Resolución gobernada en la seam de composición de F1. Default off
        # = byte-idéntico; on exige IDENTITY_RESOLVE=on (interlock fail-fast en
        # turn_resolve_enabled + chequeo de boot).
        "default_fuente": '""',
        "via": ['getenv'],
        "lectores": ('src/rag/catalog_resolver.py',),
    },
    "GENERATOR_DIRECT_FIRST": {
        "default_fuente": '"off"',
        "via": ['getenv'],
        "lectores": ('src/rag/generator.py',),
    },
    "GENERATOR_FOLLOWUPS": {
        "default_fuente": '"off"',
        "via": ['getenv'],
        "lectores": ('src/rag/generator.py',),
    },
    "GENERATOR_INCLUDE_CONTEXT": {
        "default_fuente": 'None',
        "via": ['getenv'],
        "lectores": ('src/rag/generator.py',),
    },
    "GENERATOR_PROMPT_VARIANT": {
        "default_fuente": '"fidelity"',
        "via": ['getenv'],
        "lectores": ('src/rag/generator.py',),
    },
    "GENERATOR_SELECTION_BLOCK": {
        "default_fuente": '"off"',
        "via": ['getenv'],
        "lectores": ('src/rag/generator.py',),
    },
    "HYDE_ENABLED": {
        "default_fuente": '"false"',
        "via": ['getenv'],
        "lectores": ('src/rag/hyde.py',),
    },
    "HYDE_MODEL": {
        "default_fuente": '"claude-haiku-4-5"',
        "via": ['getenv'],
        "lectores": ('src/rag/hyde.py',),
    },
    "HYQ_PILOT_FILE": {
        "default_fuente": '""',
        "via": ['getenv'],
        "lectores": ('src/rag/retriever.py',),
    },
    "HYQ_PILOT_MIN_COS": {
        "default_fuente": '"0.45"',
        "via": ['getenv'],
        "lectores": ('src/rag/retriever.py',),
    },
    "HYQ_PILOT_QUOTA": {
        "default_fuente": '"10"',
        "via": ['getenv'],
        "lectores": ('src/rag/retriever.py',),
    },
    "HYQ_TABLE": {
        "default_fuente": '"on"',
        "via": ['getenv'],
        "lectores": ('src/rag/retriever.py',),
    },
    "EC_LEGAL_DISCLAIMER_SKIP": {
        "default_fuente": '""',
        "via": ['getenv'],
        "lectores": ('src/rag/evidence_contract.py',),
    },
    "HTTP_POOL": {
        "default_fuente": '"on"',
        "via": ['getenv'],
        "lectores": ('src/http_pool.py',),
    },
    "HTTP_RETRIES": {
        "default_fuente": '"on"',
        "via": ['getenv'],
        "lectores": ('src/http_pool.py',),
    },
    "RETRIEVAL_PARALLEL": {
        "default_fuente": '"on"',
        "via": ['getenv'],
        "lectores": ('src/rag/retriever.py',),
    },
    "INTENT_LLM": {
        "default_fuente": '""',
        "via": ['getenv'],
        "lectores": ('src/bot/telegram_bot.py',),
    },
    "IDENTITY_FETCH": {
        "default_fuente": '""',
        "via": ['getenv'],
        "lectores": ('src/rag/catalog_resolver.py',),
    },
    "IDENTITY_MAP": {
        "default_fuente": '""',
        "via": ['getenv', 'legacy-flags-loop'],
        "lectores": ('src/rag/catalog_resolver.py', 'src/rag/retriever.py'),
    },
    "IDENTITY_RESOLVE": {
        "default_fuente": '""',
        "via": ['getenv'],
        "lectores": ('src/rag/catalog_resolver.py',),
    },
    "IDENTITY_RESOLVE_POLICY": {
        "default_fuente": '""',
        "via": ['getenv'],
        "lectores": ('src/config.py', 'src/rag/catalog_resolver.py'),
        "divergencia": ['""', 'None'],  # VISIBLE a proposito (L2b: el pin detecta, no corrige)
    },
    "IMAGES_DIR": {
        "default_fuente": 'PROJECT_DIR / "extracted_images"',
        "via": ['getenv'],
        "lectores": ('src/config.py',),
    },
    "LEVER1_KEYWORD_ORDER": {
        "default_fuente": '""',
        "via": ['getenv'],
        "lectores": ('src/rag/retriever.py',),
    },
    "LEVER2_IDENTITY": {
        "default_fuente": '""',
        "via": ['getenv', 'legacy-flags-loop', 'series-registry-yaml:morley.yaml'],
        "lectores": ('src/rag/catalog_resolver.py', 'src/rag/retriever.py', 'src/rag/series_registry.py'),
    },
    "LEVER2_PM_RESCUE": {
        "default_fuente": '""',
        "via": ['getenv', 'legacy-flags-loop'],
        "lectores": ('src/rag/catalog_resolver.py', 'src/rag/retriever.py'),
    },
    "LLM_MAX_TOKENS": {
        "default_fuente": '"3500"',
        "via": ['getenv'],
        "lectores": ('src/config.py',),
    },
    "LLM_MODEL": {
        "default_fuente": '"claude-sonnet-4-6"',
        "via": ['getenv'],
        "lectores": ('src/config.py',),
    },
    "LOGICAL_RECORD_COVERAGE": {
        "default_fuente": '"off"',
        "via": ['strict_on_off'],
        "lectores": ('src/config.py',),
    },
    "MANUALS_DIR": {
        "default_fuente": 'PROJECT_DIR / "Manuales_ES"',
        "via": ['getenv'],
        "lectores": ('src/config.py',),
    },
    "MERGE_STRATEGY": {
        "default_fuente": '"stamps"',
        "via": ['getenv'],
        "lectores": ('src/config.py',),
    },
    # s324e — lever de la conducta (a) ante marca<->producto erronea (DEC-224 §B,
    # alcance (a) de DEC-226): con ON, un turno con UNA marca y UN modelo que no
    # casan se corrige Y se responde en el mismo turno; con OFF (default) el bot
    # hace lo de hoy, byte a byte. Nace OFF porque `main` auto-despliega y esta es
    # conducta SERVIDA: el flip lo decide Alberto tras el smoke. Lo LEE el accessor
    # de este mismo modulo (`mismatch_answer_activo`) y entra al planificador como
    # dato (`Meta.mismatch_answer`) — `plan_turn` es PURA y no lee entorno.
    "MISMATCH_ANSWER": {
        "default_fuente": '"off"',
        "via": ['getenv'],
        "lectores": ('src/flags.py',),
    },
    "MP_DEFLINE_EQ": {
        "default_fuente": '"off"',
        "via": ['mp_flag'],
        "lectores": ('src/rag/must_preserve.py',),
    },
    "MP_DISTINCTIVE_TOKEN": {
        "default_fuente": '"off"',
        "via": ['mp_flag'],
        "lectores": ('src/rag/must_preserve.py',),
    },
    "MP_HYBRID_DETECT": {
        "default_fuente": '"off"',
        "via": ['mp_flag'],
        "lectores": ('src/rag/must_preserve.py',),
    },
    "MP_MANDATORY_VERB_TRIGGER": {
        "default_fuente": '"off"',
        "via": ['mp_flag', 'profile-owned-loop'],
        "lectores": ('src/rag/must_preserve.py', 'src/release_profiles.py'),
    },
    "MP_SERVED_BINDING": {
        "default_fuente": '"off"',
        "via": ['mp_flag'],
        "lectores": ('src/rag/must_preserve.py',),
    },
    "MP_STEM_BINDING": {
        "default_fuente": '"off"',
        "via": ['mp_flag'],
        "lectores": ('src/rag/must_preserve.py',),
    },
    "MUST_PRESERVE_CONTRACT": {
        "default_fuente": '"off"',
        "via": ['strict_on_off'],
        "lectores": ('src/config.py', 'src/rag/must_preserve.py'),
    },
    "NEIGHBOR_MODELS_ONLY": {
        "default_fuente": '""',
        "via": ['getenv'],
        "lectores": ('src/rag/retriever.py',),
    },
    "NEIGHBOR_WINDOW": {
        "default_fuente": '"0"',
        "via": ['getenv'],
        "lectores": ('src/rag/retriever.py',),
    },
    "OBLIGATION_RESERVE_ORDERED": {
        "default_fuente": '"off"',
        "via": ['strict_on_off'],
        "lectores": ('src/rag/obligation_warning.py', 'src/release_profiles.py'),
    },
    "OBLIGATION_WARNING_APPENDIX": {
        "default_fuente": '"off"',
        "via": ['mp_flag', 'strict_on_off'],
        "lectores": ('src/rag/must_preserve.py', 'src/release_profiles.py'),
    },
    "OBLIGATION_WARNING_RESERVE": {
        "default_fuente": '"off"',
        "via": ['profile-owned-loop'],
        "lectores": ('src/release_profiles.py',),
    },
    "OPENAI_API_KEY": {
        "default_fuente": '""',
        "via": ['getenv'],
        "lectores": ('src/config.py',),
        "sensible": True,
    },
    "POST_RERANK_COVERAGE": {
        "default_fuente": '"off"',
        "via": ['profile-owned-loop'],
        "lectores": ('src/release_profiles.py',),
    },
    "PROSE_SOURCE_CARD": {
        "default_fuente": '"off"',
        "via": ['profile-owned-loop', 'strict_on_off'],
        "lectores": ('src/rag/document_local_coverage.py', 'src/rag/post_rerank_coverage.py', 'src/release_profiles.py'),
    },
    "R2_REPAIR_NAVIGATION": {
        "default_fuente": '"off"',
        "via": ['strict_on_off'],
        "lectores": ('src/config.py',),
    },
    "RAILWAY_GIT_COMMIT_SHA": {
        "default_fuente": '""',
        "via": ['getenv'],
        "lectores": ('src/version.py',),
    },
    "RERANKER_BACKEND": {
        "default_fuente": '"llm"',
        "via": ['getenv'],
        "lectores": ('src/config.py',),
    },
    "RERANK_POOL_COVERAGE": {
        "default_fuente": '"off"',
        "via": ['strict_on_off'],
        "lectores": ('src/config.py',),
    },
    "RERANK_PREVIEW_CHARS": {
        "default_fuente": '"800"',
        "via": ['getenv'],
        "lectores": ('src/config.py',),
    },
    "RERANK_TOP_K": {
        "default_fuente": '"10"',
        "via": ['getenv'],
        "lectores": ('src/config.py',),
    },
    "REWRITER_MODEL": {
        "default_fuente": '"claude-sonnet-4-6"',
        "via": ['getenv'],
        "lectores": ('src/config.py',),
    },
    "SERIES_REGISTRY_ENABLED": {
        "default_fuente": '"true"',
        "via": ['getenv'],
        "lectores": ('src/rag/series_registry.py',),
    },
    "SOURCE_LEGEND": {
        "default_fuente": '"off"',
        "via": ['getenv', 'strict_on_off'],
        "lectores": ('src/rag/generator.py', 'src/rag/source_legend.py'),
    },
    "SOURCE_LEGEND_LINKS": {
        "default_fuente": '"off"',
        "via": ['strict_on_off'],
        "lectores": ('src/rag/source_legend.py',),
    },
    "STRUCK_OCR_CONTEXT": {
        "default_fuente": '"off"',
        "via": ['strict_on_off'],
        "lectores": ('src/rag/generator.py',),
    },
    "STRUCTURAL_CASCADE_COVERAGE": {
        "default_fuente": '"off"',
        "via": ['strict_on_off'],
        "lectores": ('src/config.py',),
    },
    "STRUCTURAL_NEIGHBOR_COVERAGE": {
        "default_fuente": '"off"',
        "via": ['profile-owned-loop'],
        "lectores": ('src/release_profiles.py',),
    },
    "STRUCTURAL_NEIGHBOR_SHADOW": {
        "default_fuente": '"off"',
        "via": ['strict_on_off'],
        "lectores": ('src/config.py',),
    },
    "STRUCTURAL_NEIGHBOR_SHADOW_HMAC_KEY": {
        "default_fuente": '""',
        "via": ['getenv'],
        "lectores": ('src/config.py',),
        "sensible": True,
    },
    "STRUCTURAL_NEIGHBOR_SHADOW_HMAC_KEY_VERSION": {
        "default_fuente": '""',
        "via": ['getenv'],
        "lectores": ('src/config.py',),
        "sensible": True,
    },
    "SUPABASE_KEY": {
        "default_fuente": '""',
        "via": ['getenv'],
        "lectores": ('src/config.py',),
        "sensible": True,
    },
    "SUPABASE_SERVICE_KEY": {
        "default_fuente": '""',
        "via": ['getenv'],
        # s323 fase C: + rag/identidad_gate.py — el gate de invariantes consulta
        # la DB viva (lectura PEREZOSA: leerlas al importar habria roto la CI,
        # que corre pytest sin secretos — critico del duo r34).
        # s325b: + extraction_store.py — el resolutor lee del bucket
        # `extraction` cuando no hay store en disco (sesion cloud). Lectura
        # PEREZOSA por el mismo motivo que el gate: importar no debe exigir
        # credenciales, que la CI corre sin ellas.
        "lectores": ('src/config.py', 'src/extraction_store.py',
                     'src/rag/identidad_gate.py'),
        "sensible": True,
        # DIVERGENCIA declarada (s323 fase C): config.py usa default "" y el gate
        # las exige con os.environ[...] — sin credenciales NO se puede evaluar, y
        # "no he podido comprobar" NO es "todo bien" (critico del duo r34). El
        # pin DETECTA, no corrige: la divergencia es deliberada y visible.
        "divergencia": ['""', 'KeyError'],
    },
    "SUPABASE_URL": {
        "default_fuente": '""',
        "via": ['getenv'],
        # s323 fase C: + rag/identidad_gate.py — el gate de invariantes consulta
        # la DB viva (lectura PEREZOSA: leerlas al importar habria roto la CI,
        # que corre pytest sin secretos — critico del duo r34).
        # s325b: + extraction_store.py — el resolutor lee del bucket
        # `extraction` cuando no hay store en disco (sesion cloud). Lectura
        # PEREZOSA por el mismo motivo que el gate: importar no debe exigir
        # credenciales, que la CI corre sin ellas.
        "lectores": ('src/config.py', 'src/extraction_store.py',
                     'src/rag/identidad_gate.py'),
        "sensible": True,
        # DIVERGENCIA declarada (s323 fase C): config.py usa default "" y el gate
        # las exige con os.environ[...] — sin credenciales NO se puede evaluar, y
        # "no he podido comprobar" NO es "todo bien" (critico del duo r34). El
        # pin DETECTA, no corrige: la divergencia es deliberada y visible.
        "divergencia": ['""', 'KeyError'],
    },
    "TABLE_PREAMBLE_CLOSURE": {
        "default_fuente": '"off"',
        "via": ['strict_on_off'],
        "lectores": ('src/config.py',),
    },
    "TELEGRAM_BOT_TOKEN": {
        "default_fuente": '""',
        "via": ['getenv'],
        "lectores": ('src/config.py',),
        "sensible": True,
    },
    # s329 — OVERRIDE del username publico del bot para el enlace de invitacion.
    # El default real NO esta aqui: es `access.BOT_USERNAME_DEFECTO` en codigo
    # (identidad publica verificada contra getMe), asi el enlace sale completo
    # sin configurar nada; esta variable existe para apuntar a un bot de pruebas.
    "TELEGRAM_BOT_USERNAME": {
        "default_fuente": 'None',
        "via": ['getenv'],
        "lectores": ('src/bot/access.py',),
    },
    "TELEGRAM_FEEDBACK": {
        "default_fuente": '"off"',
        "via": ['getenv'],
        "lectores": ('src/bot/telegram_bot.py',),
    },
    "TELEGRAM_FEEDBACK_REASON": {
        "default_fuente": '"off"',
        "via": ['getenv'],
        "lectores": ('src/bot/telegram_bot.py',),
    },
    "VISUAL_ASSETS_LISTING_GATE": {
        "default_fuente": '"off"',
        "via": ['getenv'],
        "lectores": ('src/rag/generator.py',),
    },
    "VISUAL_ASSETS_REGISTRY": {
        "default_fuente": '"off"',
        "via": ['strict_on_off'],
        "lectores": ('src/config.py',),
    },
    "VOICE_TRANSCRIPTION_MODEL": {
        "default_fuente": '"whisper-1"',
        "via": ['getenv'],
        "lectores": ('src/config.py',),
    },
    "VOYAGE_API_KEY": {
        "default_fuente": 'None',
        "via": ['getenv'],
        "lectores": ('src/rag/reranker.py', 'src/reingest/embed.py'),
        "sensible": True,
    },
    "WIRING_TOPOLOGY_GUARD": {
        "default_fuente": '"on"',
        "via": ['getenv'],
        "lectores": ('src/rag/generator.py',),
    },
}


def mismatch_answer_activo() -> bool:
    """Lever MISMATCH_ANSWER (s324e), leido en RUNTIME (un flip en Railway togglea
    sin restart, como CONVERSATION_POLICY).

    Vive AQUI y no en el transporte a proposito: `plan_turn` es una funcion PURA
    (el flag entra por `Meta`), la voz entrara por otra puerta, y una lectura de
    entorno por call-site es justo la deriva que el registro L2b existe para
    evitar. Parser ESTRICTO (precedente r19/Sol M1 en `conversation_policy_active`
    y `_strict_on_off`): un typo en Railway no puede dejar el lever a medias EN
    SILENCIO — revienta RUIDOSO. El default "off" hace que la ausencia de la
    variable sea la conducta de hoy."""
    raw = os.getenv("MISMATCH_ANSWER", "off").strip().lower()
    if raw == "on":
        return True
    if raw == "off":
        return False
    raise RuntimeError(f"MISMATCH_ANSWER={raw!r} no reconocido (on|off) — fail-fast")


def snapshot() -> dict[str, str]:
    """Estado actual del entorno según el registro, SIN secretos."""
    salida: dict[str, str] = {}
    for nombre, spec in REGISTRO.items():
        crudo = os.getenv(nombre)
        if spec.get("sensible"):
            salida[nombre] = "(presente)" if crudo is not None else "(ausente)"
        elif crudo is None:
            salida[nombre] = "(default: " + spec["default_fuente"] + ")"
        else:
            salida[nombre] = crudo
    return salida
