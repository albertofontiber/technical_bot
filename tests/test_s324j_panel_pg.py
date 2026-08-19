# -*- coding: utf-8 -*-
"""s324j — El panel contra un PostgreSQL REAL: la puerta 4 de
`evals/s324i_panel_vercel_propuesta_v9.md`.

Por qué existe: el resto de puertas del panel usan dobles, así que prueban que
se emiten las sentencias correctas — no que la base haga lo que decimos. Y lo
dicho es fuerte: que `panel_puerta` acota el rebaño concurrente, que el cap es
un techo, que la ventana de retención es un invariante del MOTOR (política,
no SQL de la pasada), y que la frontera ACL de las tablas nuevas es efectiva.
Verificar el EFECTO y no el código — la lección #60 (mismo patrón que
`test_s295_rgpd_integracion_pg.py`, cuyo arnés se REUTILIZA: la 019 exige la
cola s295→s299 aplicada, y ese arnés la aplica ENTERA y en orden, ronda S5-M2).

Se salta sin `RGPD_TEST_DATABASE_URL`; en CI lo provee un contenedor
desechable (`.github/workflows/s324j-panel-pg.yml`). NUNCA producción.

GAP DECLARADO (v9 §12): el contenedor es Postgres, no Supabase — PostgREST y
su caché solo se prueban en el smoke post-deploy del runbook.
"""
from __future__ import annotations

import os
import threading
from pathlib import Path

import pytest

from dashboard import auth

# El arnés canónico: esquema mínimo + roles del trío de la API (service_role
# CON BYPASSRLS, como en Supabase — sin él, panel_puerta bajo FORCE RLS vería
# cero filas y este test probaría un mundo que no existe) + default privileges
# de Supabase reproducidos + la cola s295→s299 aplicada EN ORDEN.
from tests.test_s295_rgpd_integracion_pg import base  # noqa: F401

REPO = Path(__file__).parent.parent
M016 = REPO / "migrations" / "016_allowlist_invitaciones.sql"
M019 = REPO / "migrations" / "019_panel_usuarios_cerrojo.sql"
M020 = REPO / "migrations" / "020_invitaciones_op.sql"

DSN = os.environ.get("RGPD_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DSN,
    reason="requiere RGPD_TEST_DATABASE_URL (Postgres desechable); en CI lo da el workflow",
)

#: token_hash de las dos filas LEGACY. La 016 CANÓNICA lo exige `^[0-9a-f]{64}$`
#: por CHECK; la copia estrecha que había antes NO lo tenía (ni el CHECK de
#: caducidad ≤ 7 días), y EN CAMBIO imponía `nota NOT NULL` donde la 016 real la
#: deja NULLable — divergía en AMBOS sentidos. Es justo lo que S-M3 cazó: la 020
#: se probaba contra una 016 de ficción. Ahora el fixture aplica la 016 real (ver
#: abajo), así que estos hashes tienen que ser hex de 64.
TH_ANULADA = "a" * 64
TH_VIVA = "b" * 64

CONSTANTES = dict(libres=auth.FALLOS_LIBRES, base_s=auth.BLOQUEO_BASE_S,
                  max_s=auth.BLOQUEO_MAX_S,
                  retencion_s=auth.CERROJO_RETENCION_S,
                  cap=auth.CERROJO_MAX_ENTRADAS)


def _conectar():
    import psycopg2
    return psycopg2.connect(DSN, connect_timeout=15)


@pytest.fixture()
def panel(base):  # noqa: F811
    """El arnés s295→s299 + invitaciones legacy + las 019/020 aplicadas."""
    conexion, _, _ = base
    conexion.autocommit = True
    with conexion.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS panel_intentos, panel_usuarios CASCADE;")
        cur.execute("DROP FUNCTION IF EXISTS public.panel_retencion_pasada(TEXT);")
        cur.execute("DROP FUNCTION IF EXISTS public.panel_puerta"
                    "(text[], int, numeric, numeric, numeric, int);")
        # La 016 CANÓNICA, no una copia estrecha (ronda sello-final, S-M3): así
        # la 020 se prueba contra la MISMA DDL/ACL/CHECK que producción. Se
        # dropean las dos tablas de la 016 (la crea con IF NOT EXISTS) para que
        # el fixture sea idempotente entre tests. El bootstrap de la 016 lee
        # user_consent del `base` — cuyos INSERT NO ponen display_name (columna
        # NULLable): no revienta porque la 016 hace COALESCE(display_name, '(sin
        # nombre)') (016:258, lo señaló el 2º frontera en la adjudicación). Solo
        # puebla bot_allowlist, que ningún test del panel mide.
        cur.execute("DROP TABLE IF EXISTS bot_allowlist, bot_invitaciones CASCADE;")
        cur.execute(M016.read_text("utf-8"))
        # Dos filas LEGACY: una anulada sin firma (el mundo pre-020) y una viva
        # — el backfill y el default volátil por fila tienen que cubrirlas. El
        # token_hash es hex de 64 porque la 016 real lo exige por CHECK.
        cur.execute(
            "INSERT INTO bot_invitaciones (token_hash, nota, creada_por, "
            "expira_at, revocada_at) VALUES "
            "(%s, 'legacy anulada', 'cli:x', now() + interval '1 day', now()),"
            "(%s, 'legacy viva', 'cli:x', now() + interval '1 day', NULL);",
            (TH_ANULADA, TH_VIVA))
        cur.execute(M019.read_text("utf-8"))
        cur.execute(M020.read_text("utf-8"))
    conexion.autocommit = False
    yield conexion
    conexion.close()


def _puerta(cur, claves, **cambios):
    args = {**CONSTANTES, **cambios}
    cur.execute(
        "SELECT public.panel_puerta(%s::text[], %s, %s, %s, %s, %s)",
        (claves, args["libres"], args["base_s"], args["max_s"],
         args["retencion_s"], args["cap"]))
    return float(cur.fetchone()[0])


def _como_service_role(conexion):
    cur = conexion.cursor()
    cur.execute("SET LOCAL ROLE service_role;")
    return cur


# ----------------------------------------------------- aplicación y frontera


def test_las_migraciones_aplican_con_sus_postcondiciones(panel):
    """El fixture ya lo prueba (una postcondición rota revienta el `execute`
    del fichero entero); aquí se afirma el resultado visible."""
    with panel.cursor() as cur:
        cur.execute("SELECT to_regclass('public.panel_usuarios'), "
                    "to_regclass('public.panel_intentos')")
        assert all(cur.fetchone())
    panel.rollback()


def test_privilegios_EFECTIVOS_por_rol(panel):
    """Ronda S5-M3: la puerta 9 fija lo que las migraciones DICEN; esto, lo que
    la base HACE — has_table_privilege/has_column_privilege por cada rol."""
    with panel.cursor() as cur:
        for rol in ("anon", "authenticated"):
            for tabla in ("panel_usuarios", "panel_intentos"):
                cur.execute(
                    "SELECT has_table_privilege(%s, %s, "
                    "'SELECT, INSERT, UPDATE, DELETE')", (rol, tabla))
                assert cur.fetchone()[0] is False, (rol, tabla)
        # service_role: EXACTAMENTE lo enumerado.
        cur.execute("SELECT has_column_privilege('service_role', "
                    "'panel_usuarios', 'registro', 'SELECT')")
        assert cur.fetchone()[0] is True
        cur.execute("SELECT has_column_privilege('service_role', "
                    "'panel_usuarios', 'alta_por', 'SELECT')")
        assert cur.fetchone()[0] is False        # la auditoría no viaja a REST
        cur.execute("SELECT has_column_privilege('service_role', "
                    "'panel_usuarios', 'alta_por', 'UPDATE')")
        assert cur.fetchone()[0] is False        # ...ni se reescribe
        cur.execute("SELECT has_table_privilege('service_role', "
                    "'panel_usuarios', 'DELETE')")
        assert cur.fetchone()[0] is False        # baja lógica, sin DELETE
        cur.execute("SELECT has_table_privilege('service_role', "
                    "'panel_intentos', 'DELETE')")
        assert cur.fetchone()[0] is True         # el contrato del cerrojo
        # rgpd_retencion: solo lo suyo.
        cur.execute("SELECT has_column_privilege('rgpd_retencion', "
                    "'panel_intentos', 'clave', 'SELECT')")
        assert cur.fetchone()[0] is True
        cur.execute("SELECT has_table_privilege('rgpd_retencion', "
                    "'panel_usuarios', 'SELECT')")
        assert cur.fetchone()[0] is False
    panel.rollback()


def test_un_rol_de_la_api_no_puede_ejecutar_las_funciones(panel):
    with panel.cursor() as cur:
        for rol in ("anon", "authenticated"):
            cur.execute(
                "SELECT has_function_privilege(%s, 'public.panel_puerta("
                "text[], int, numeric, numeric, numeric, int)', 'EXECUTE')",
                (rol,))
            assert cur.fetchone()[0] is False, rol
            cur.execute(
                "SELECT has_function_privilege(%s, "
                "'public.panel_retencion_pasada(text)', 'EXECUTE')", (rol,))
            assert cur.fetchone()[0] is False, rol
        cur.execute("SELECT has_function_privilege('service_role', "
                    "'public.panel_retencion_pasada(text)', 'EXECUTE')")
        assert cur.fetchone()[0] is False        # ni la API ejecuta la pasada
    panel.rollback()


# ------------------------------------------------------- la semántica, REAL


def test_la_tabla_de_casos_secuencial(panel):
    """La misma tabla que el doble en memoria (puerta 4b): 5 admitidos, el
    sexto bloqueado con el primer castigo, sin incremento al estar bloqueado."""
    with _como_service_role(panel) as cur:
        for _ in range(auth.FALLOS_LIBRES + 1):
            assert _puerta(cur, ["u:caso"]) == 0.0
        espera = _puerta(cur, ["u:caso"])
        assert 0 < espera <= auth.BLOQUEO_BASE_S
        cur.execute("SELECT fallos FROM panel_intentos WHERE clave='u:caso'")
        assert cur.fetchone()[0] == auth.FALLOS_LIBRES + 1   # bloqueado no suma
    panel.rollback()


def test_la_rafaga_concurrente_sobre_clave_fresca_admite_libres_mas_uno(panel):
    """EL rebaño (rondas M1/S-C3): N hilos, N conexiones, la MISMA clave
    fresca. Sin siembra-antes-del-lock y sin contar-al-admitir entrarían N."""
    panel.rollback()
    resultados = []
    barrera = threading.Barrier(12)

    def intento():
        conexion = _conectar()
        try:
            with conexion.cursor() as cur:
                cur.execute("SET ROLE service_role;")
                barrera.wait(timeout=30)
                cur.execute(
                    "SELECT public.panel_puerta(%s::text[], %s, %s, %s, %s, %s)",
                    (["u:rafaga"], CONSTANTES["libres"], CONSTANTES["base_s"],
                     CONSTANTES["max_s"], CONSTANTES["retencion_s"],
                     CONSTANTES["cap"]))
                resultados.append(float(cur.fetchone()[0]))
            conexion.commit()
        finally:
            conexion.close()

    hilos = [threading.Thread(target=intento) for _ in range(12)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join(timeout=60)
    admitidos = sum(1 for r in resultados if r == 0.0)
    assert len(resultados) == 12
    assert admitidos == auth.FALLOS_LIBRES + 1, resultados


def test_el_upsert_recrea_la_fila_que_acierto_borro(panel):
    """Ronda S6-M2: el DELETE de `acierto` corre FUERA del advisory lock y
    puede borrar la fila. Este test modela el EFECTO de ese entrelazado con un
    DELETE secuencial (no reproduce la carrera — honestidad de test, ronda de
    verificación S3-m1): el upsert-siempre recrea la fila con fallos=1, así que
    la admisión que sigue nunca queda sin contar. Que el upsert sea correcto
    BAJO la carrera lo sostiene READ COMMITTED + el advisory lock, no este
    test."""
    with _como_service_role(panel) as cur:
        for _ in range(3):
            assert _puerta(cur, ["u:leg"]) == 0.0
        cur.execute("DELETE FROM panel_intentos WHERE clave = 'u:leg'")  # acierto
        assert _puerta(cur, ["u:leg"]) == 0.0
        cur.execute("SELECT fallos FROM panel_intentos WHERE clave='u:leg'")
        assert cur.fetchone()[0] == 1            # renació contada
    panel.rollback()


def test_acierto_concurrente_no_deja_admisiones_sin_contar(panel):
    """Ronda sello-final, S-M2: v9 §4(c) (líneas 908-910) pide EJERCITAR con hilos
    el DELETE concurrente `acierto`↔`admitir`. Un hilo martillea `admitir` sobre
    una clave mientras otro corre `acierto` (DELETE) sobre la MISMA.

    QUÉ PRUEBA Y QUÉ NO (ronda seguimiento, Sol): la discriminación DETERMINISTA de
    «upsert, no UPDATE» vive en `test_el_upsert_recrea_la_fila_que_acierto_borro`
    (secuencial): borra la fila y afirma que el siguiente `admitir` la RECREA con
    fallos=1. ESTE test AÑADE cobertura de ESTRÉS bajo concurrencia real; es
    PROBABILÍSTICO, NO determinista: no se puede pausar la función compilada entre
    su check y su upsert desde fuera, así que NO se FUERZA la ventana
    check→DELETE→upsert —una corrida podría no tocarla (el borrador cayendo entre
    RPC ya cerradas)—. No afirma «ventana ejercida» ni sella el contrato de
    concurrencia por sí solo; martillea `N` veces para hacerla PROBABLE.

    Lo que sí verifica (en LOCAL; no hay recibo de CI adjunto) es una LEY DE
    CONSERVACIÓN que un `admitir` correcto cumple y uno UPDATE-en-vez-de-upsert
    rompe SI el DELETE cae en la ventana: cada `admitir` que ADMITE (0) suma 1;
    cada bloqueado (>0) no suma; cada `acierto` retira los `fallos` que borra. Con
    una fila SEMBRADA (`fallos=1`) y un borrador do-while (corre ≥1 vez), el DELETE
    retira SIEMPRE al menos esa fila viva → liveness determinista, sin rojo
    espurio:

        sembrado(1) + admitidos == fallos_finales + retirados"""
    panel.rollback()
    SEMBRADO = 1
    with _como_service_role(panel) as cur:               # una fila viva de arranque
        cur.execute("INSERT INTO panel_intentos (clave, fallos, ultimo) "
                    "VALUES ('u:carrera', %s, now())", (SEMBRADO,))
    panel.commit()                                       # visible a las conexiones de los hilos
    N = 300
    fin = threading.Event()
    admitidos = []            # un 0.0 por cada admisión
    retirados = [0]           # suma de `fallos` que los aciertos retiraron
    hechas = [0]              # admisiones que el martillo COMPLETÓ (debe llegar a N)
    errores = []              # excepción de CUALQUIER hilo → el test NO pasa en vacío
    barrera = threading.Barrier(2)

    def martillo_admitir():
        conexion = _conectar()
        try:
            with conexion.cursor() as cur:
                cur.execute("SET ROLE service_role;")
                barrera.wait(timeout=30)
                for _ in range(N):
                    cur.execute(
                        "SELECT public.panel_puerta(%s::text[], %s, %s, %s, %s, %s)",
                        (["u:carrera"], CONSTANTES["libres"], CONSTANTES["base_s"],
                         CONSTANTES["max_s"], CONSTANTES["retencion_s"],
                         CONSTANTES["cap"]))
                    if float(cur.fetchone()[0]) == 0.0:
                        admitidos.append(0.0)
                    conexion.commit()
                    hechas[0] += 1
        except Exception as exc:                     # noqa: BLE001 — ningún fallo del hilo pasa por verde
            errores.append(("admitir", repr(exc)))
        finally:
            fin.set()
            conexion.close()

    def martillo_acierto():
        conexion = _conectar()
        try:
            with conexion.cursor() as cur:
                cur.execute("SET ROLE service_role;")
                barrera.wait(timeout=30)
                while True:                          # do-while: corre al menos UNA vez
                    cur.execute("DELETE FROM panel_intentos "
                                "WHERE clave='u:carrera' RETURNING fallos")
                    fila = cur.fetchone()
                    if fila is not None:
                        retirados[0] += fila[0]
                    conexion.commit()
                    if fin.is_set():
                        break
        except Exception as exc:                     # noqa: BLE001
            errores.append(("acierto", repr(exc)))
        finally:
            conexion.close()

    hilos = [threading.Thread(target=martillo_admitir),
             threading.Thread(target=martillo_acierto)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join(timeout=90)

    # Los hilos TERMINARON de verdad (un `join` con timeout no lo garantiza) y
    # ninguno murió por dentro: sin estas tres guardas una ejecución parcial o un
    # hilo caído podría satisfacer la ley de conservación en vacío (ronda
    # seguimiento, Sol sobre el rigor de S-M2).
    assert not errores, errores
    assert all(not h.is_alive() for h in hilos), "un hilo no terminó en 90s"
    assert hechas[0] == N, hechas[0]                      # el martillo hizo las N admisiones

    with panel.cursor() as cur:
        cur.execute("SELECT COALESCE(SUM(fallos), 0) FROM panel_intentos "
                    "WHERE clave='u:carrera'")
        finales = cur.fetchone()[0]
    panel.rollback()

    assert len(admitidos) >= 1                            # hubo admisiones
    assert retirados[0] >= SEMBRADO                       # el borrador retiró al menos la fila sembrada
    assert SEMBRADO + len(admitidos) == finales + retirados[0], (
        SEMBRADO, len(admitidos), finales, retirados[0])  # ninguna admisión sin contar


def test_el_cap_es_un_techo_con_la_aritmetica_exacta(panel):
    """Ronda S2-M3: count + nuevas <= cap — no «si está al cap»."""
    with _como_service_role(panel) as cur:
        for i in range(5):
            _puerta(cur, [f"u:v{i}"], cap=5)
        cur.execute("SELECT count(*) FROM panel_intentos")
        assert cur.fetchone()[0] == 5
        _puerta(cur, ["u:nueva-a", "u:nueva-b"], cap=5)
        cur.execute("SELECT count(*) FROM panel_intentos")
        assert cur.fetchone()[0] <= 5            # sacrificó lo más viejo
        cur.execute("SELECT 1 FROM panel_intentos WHERE clave = 'u:nueva-b'")
        assert cur.fetchone()                    # y la siembra nueva cupo
    panel.rollback()


def test_el_cap_no_sacrifica_una_clave_de_la_propia_admision(panel):
    """Ronda sello-final, S-M1: el caso que el test de arriba NO cubría —dos
    claves totalmente nuevas—. Con la tabla llena y una admisión `[u:existente,
    u:nueva]` donde la existente es la MÁS ANTIGUA, el DELETE del cap no puede
    sacrificarla: el upsert la recrearía y la tabla acabaría en `cap+1`. Con la
    exclusión `clave <> ALL(claves)` el techo es EXACTO. Timestamps sembrados a
    mano para que el orden por `ultimo` sea determinista (no depende del reloj)."""
    with _como_service_role(panel) as cur:
        cur.execute(
            "INSERT INTO panel_intentos (clave, fallos, ultimo) VALUES "
            "('u:viejo', 1, now() - interval '50 min'),"
            "('u:v1', 1, now() - interval '40 min'),"
            "('u:v2', 1, now() - interval '30 min'),"
            "('u:v3', 1, now() - interval '20 min'),"
            "('u:v4', 1, now() - interval '10 min')")   # tabla llena (5), u:viejo el más antiguo
        _puerta(cur, ["u:viejo", "u:nueva"], cap=5)      # existente-antigua + nueva
        cur.execute("SELECT count(*) FROM panel_intentos")
        assert cur.fetchone()[0] == 5                    # EXACTO en cap — sin la fuga de +1
        cur.execute("SELECT clave FROM panel_intentos ORDER BY clave")
        vivas = [f[0] for f in cur.fetchall()]
        assert "u:viejo" in vivas                        # NO se sacrificó la clave de la admisión
        assert "u:nueva" in vivas                        # la nueva cupo
        assert "u:v1" not in vivas                        # se sacrificó la más vieja que SÍ podía irse
    panel.rollback()


@pytest.mark.parametrize("claves,cap", [
    (["u:a", "u:b", "u:c"], 2),   # cardinality(3) > cap(2)
    (["u:a"], None),              # cap NULL (ronda 3 de Sol)
    (None, 5),                    # claves NULL (ronda 4 de Sol)
])
def test_el_guard_del_techo_rechaza_entradas_invalidas(panel, claves, cap):
    """Ronda seguimiento, Sol: el guard (0) de `panel_puerta` rechaza las TRES vías
    que romperían el techo —cardinality>cap y los dos NULL (`cap`, `claves`)— con
    CheckViolation y sin tocar la tabla. Es el CONTROL NEGATIVO de cada rama del
    `IF`: quitar cualquiera de las tres condiciones deja su caso rojo, reabriendo
    la fuga NULL/desbordamiento que declaramos cerrada. Inalcanzable en prod (≤2
    claves no-NULL, cap=miles); si pasara, >=400 → CerrojoNoDisponible → 503."""
    import psycopg2
    with _como_service_role(panel) as cur:
        with pytest.raises(psycopg2.errors.CheckViolation):
            _puerta(cur, claves, cap=cap)
    panel.rollback()
    # El discriminante es el `raises` por rama (quitar una condición del IF deja
    # su caso sin excepción). El count de abajo NO prueba el ORDEN del guard —un
    # RAISE aborta la sentencia entera atómicamente esté donde esté (lo señaló
    # el 2º frontera)—: solo documenta el estado final limpio.
    with _como_service_role(panel) as cur:
        cur.execute("SELECT count(*) FROM panel_intentos")
        assert cur.fetchone()[0] == 0
    panel.rollback()


def test_un_intento_bloqueado_no_siembra_ni_poda(panel):
    """Ronda de verificación del cableado, S2-M1: el check de bloqueo va ANTES
    de sembrar/podar — un atacante ya bloqueado por una clave (aquí `ip:`) no
    puede seguir creando filas `u:` frescas para inflar la tabla. Es el orden
    del doble en memoria; sembrar antes dejaba vivo el bypass del cap."""
    with _como_service_role(panel) as cur:
        # Bloquear la clave ip: del atacante (6 intentos = FALLOS_LIBRES+2):
        for _ in range(auth.FALLOS_LIBRES + 2):
            _puerta(cur, ["u:objetivo", "ip:atacante"])
        cur.execute("SELECT count(*) FROM panel_intentos")
        antes = cur.fetchone()[0]
        # Ahora el atacante, YA bloqueado por ip:, intenta con un usuario
        # inventado NUEVO — que sin el fix sembraría una fila más:
        espera = _puerta(cur, ["u:inventado-nuevo", "ip:atacante"])
        assert espera > 0                        # bloqueado por ip:
        cur.execute("SELECT count(*) FROM panel_intentos")
        assert cur.fetchone()[0] == antes        # NO sembró la clave nueva
        cur.execute("SELECT 1 FROM panel_intentos WHERE clave='u:inventado-nuevo'")
        assert cur.fetchone() is None
    panel.rollback()


def test_ultimo_es_del_presente_no_del_inicio_de_transaccion(panel):
    """Ronda de verificación, S2-m1 / honestidad S3-M5, S4-M4: lo que este test
    PRUEBA es que `ultimo` queda en el PRESENTE tras una ráfaga serializada —
    no retrasado al inicio de una transacción encolada. NO prueba monotonía
    fuerte (cada escritura ≥ la anterior): solo observa el valor final.
    Y la monotonía fuerte tampoco está GARANTIZADA por construcción: leer
    `clock_timestamp()` bajo el lock la hace robusta al desorden de tiempos de
    inicio de transacción —el bug que motivó el fix—, pero es reloj de PARED y
    un ajuste del sistema puede hacerlo retroceder (límite declarado en el SQL).
    El motivo del cambio `now()`→`clock_timestamp()` sigue siendo válido —quita
    el retroceso SISTEMÁTICO por tiempo de inicio de tx—; lo que no se puede
    afirmar es no-retroceso ABSOLUTO."""
    panel.rollback()
    barrera = threading.Barrier(8)

    def intento():
        conexion = _conectar()
        try:
            with conexion.cursor() as cur:
                cur.execute("SET ROLE service_role;")
                barrera.wait(timeout=30)
                cur.execute(
                    "SELECT public.panel_puerta(%s::text[], %s, %s, %s, %s, %s)",
                    (["u:mono"], CONSTANTES["libres"], CONSTANTES["base_s"],
                     CONSTANTES["max_s"], CONSTANTES["retencion_s"],
                     CONSTANTES["cap"]))
            conexion.commit()
        finally:
            conexion.close()

    hilos = [threading.Thread(target=intento) for _ in range(8)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join(timeout=60)
    # De las 8 serializadas, admiten FALLOS_LIBRES+1 (=5) y las demás se
    # bloquean sin incrementar — igual que el doble en memoria. Lo que este
    # test añade sobre `test_la_rafaga...` es la MONOTONÍA de `ultimo`: con
    # clock_timestamp() bajo el lock, la última escritura es del presente y no
    # quedó ninguna en un instante anterior (con `now()` de inicio-de-tx, una
    # llamada encolada habría escrito un `ultimo` retrasado).
    with panel.cursor() as cur:
        cur.execute("SELECT fallos, ultimo, ultimo <= clock_timestamp() "
                    "FROM panel_intentos WHERE clave='u:mono'")
        fallos, ultimo, coherente = cur.fetchone()
        assert fallos == auth.FALLOS_LIBRES + 1
        assert coherente
        cur.execute("SELECT clock_timestamp() - %s < interval '5 seconds'",
                    (ultimo,))
        assert cur.fetchone()[0], "ultimo quedó en el pasado — ¿now() en vez de clock?"
    panel.rollback()


def test_la_sonda_con_claves_vacias_no_toca_contadores(panel):
    with _como_service_role(panel) as cur:
        _puerta(cur, ["u:previa"])
        cur.execute("SELECT fallos FROM panel_intentos WHERE clave='u:previa'")
        antes = cur.fetchone()[0]
        assert _puerta(cur, []) == 0.0           # la sonda del arranque
        cur.execute("SELECT fallos FROM panel_intentos WHERE clave='u:previa'")
        assert cur.fetchone()[0] == antes
    panel.rollback()


# --------------------------------------------- la retención como INVARIANTE


def test_la_politica_impone_la_ventana_aunque_el_sql_no_la_lleve(panel):
    """La ventana vive en la POLICY (doctrina s299): el rol de retención borra
    TODO lo que puede — y solo puede lo vencido."""
    with _como_service_role(panel) as cur:
        cur.execute("INSERT INTO panel_intentos (clave, fallos, ultimo) VALUES "
                    "('u:vieja', 3, now() - interval '30 hours'), "
                    "('u:fresca', 3, now())")
    panel.commit()
    with panel.cursor() as cur:
        cur.execute("SET LOCAL ROLE rgpd_retencion;")
        cur.execute("DELETE FROM panel_intentos")        # sin WHERE, a posta
        cur.execute("RESET ROLE;")
        cur.execute("SELECT clave FROM panel_intentos")
        vivas = {fila[0] for fila in cur.fetchall()}
    panel.rollback()
    assert vivas == {"u:fresca"}


def test_la_pasada_hermana_borra_lo_vencido_y_deja_recibo(panel):
    with _como_service_role(panel) as cur:
        cur.execute("INSERT INTO panel_intentos (clave, fallos, ultimo) VALUES "
                    "('u:vencida', 2, now() - interval '25 hours'), "
                    "('u:reciente', 2, now())")
    panel.commit()
    with panel.cursor() as cur:
        cur.execute("SELECT public.panel_retencion_pasada('manual')")
        resultado = cur.fetchone()[0]
        assert resultado["panel_intentos"] == 1
        cur.execute("SELECT clave FROM panel_intentos")
        assert {f[0] for f in cur.fetchall()} == {"u:reciente"}
        cur.execute("SELECT origen, resultado FROM rgpd_recibos "
                    "ORDER BY ejecutado_at DESC LIMIT 1")
        origen, recibo = cur.fetchone()
        assert origen == "manual"
        assert recibo["panel_intentos"]["tocadas"] == 1
    panel.rollback()


def test_la_constante_python_y_la_politica_no_pueden_divergir(panel):
    """Ronda F5-M2: la ventana tiene UNA fuente (la POLICY); la constante
    `auth.CERROJO_RETENCION_S` se valida por IGUALDAD contra el predicado real
    en pg_policies — cambiar una sin la otra pone esto rojo."""
    with panel.cursor() as cur:
        cur.execute("SELECT qual FROM pg_policies WHERE schemaname='public' "
                    "AND tablename='panel_intentos' "
                    "AND policyname='rgpd_retencion_ventana'")
        qual = cur.fetchone()[0]
    panel.rollback()
    horas = auth.CERROJO_RETENCION_S // 3600
    assert auth.CERROJO_RETENCION_S % 3600 == 0
    assert f"{horas:02d}:00:00" in qual, (
        f"la POLICY dice {qual!r} y la constante {horas} h — una fuente, no dos")


# --------------------------------------------------------------- la 020, real


def test_op_backfilleado_unico_y_obligatorio(panel):
    with panel.cursor() as cur:
        cur.execute("SELECT count(*), count(DISTINCT op) FROM bot_invitaciones "
                    "WHERE op IS NOT NULL")
        total, distintos = cur.fetchone()
        assert total == 2 and distintos == 2     # el default volátil, por fila
        cur.execute("SELECT revocada_por FROM bot_invitaciones "
                    "WHERE token_hash = %s", (TH_ANULADA,))
        assert cur.fetchone()[0] == "(anterior a la 020)"
    panel.rollback()


def test_el_mismo_op_choca_con_unique_como_service_role(panel):
    import psycopg2
    with _como_service_role(panel) as cur:
        # Dos token_hash DISTINTOS (hex de 64, como exige la 016 real) con el
        # MISMO op: el segundo INSERT choca por el UNIQUE de `op`, no por el hash.
        cur.execute("INSERT INTO bot_invitaciones (token_hash, nota, "
                    "creada_por, expira_at, op) VALUES "
                    "(%s, 'x', 'panel:a', now() + interval '1 day', 'op-f5-123')",
                    ("c" * 64,))
        with pytest.raises(psycopg2.errors.UniqueViolation):
            cur.execute("INSERT INTO bot_invitaciones (token_hash, nota, "
                        "creada_por, expira_at, op) VALUES "
                        "(%s, 'x', 'panel:a', now() + interval '1 day', 'op-f5-123')",
                        ("d" * 64,))
    panel.rollback()


def test_anular_sin_firma_es_imposible_y_con_firma_funciona(panel):
    import psycopg2
    with _como_service_role(panel) as cur:
        with pytest.raises(psycopg2.errors.CheckViolation):
            cur.execute("UPDATE bot_invitaciones SET revocada_at = now() "
                        "WHERE token_hash = %s", (TH_VIVA,))
    panel.rollback()
    with _como_service_role(panel) as cur:
        cur.execute("UPDATE bot_invitaciones SET revocada_at = now(), "
                    "revocada_por = 'panel:alberto' WHERE token_hash = %s",
                    (TH_VIVA,))
        cur.execute("SELECT revocada_por FROM bot_invitaciones "
                    "WHERE token_hash = %s", (TH_VIVA,))
        assert cur.fetchone()[0] == "panel:alberto"
    panel.rollback()


def test_panel_usuarios_rechaza_lo_incoherente(panel):
    import psycopg2
    with panel.cursor() as cur:
        with pytest.raises(psycopg2.errors.CheckViolation):
            cur.execute("INSERT INTO panel_usuarios (usuario, registro, "
                        "alta_por) VALUES ('Mayuscula', 'scrypt$x', 'op')")
    panel.rollback()
    with panel.cursor() as cur:
        with pytest.raises(psycopg2.errors.CheckViolation):
            cur.execute("INSERT INTO panel_usuarios (usuario, registro, "
                        "alta_por, activo) VALUES "
                        "('coherente', 'scrypt$x', 'op', FALSE)")
    panel.rollback()
