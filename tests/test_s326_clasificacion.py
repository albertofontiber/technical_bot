# -*- coding: utf-8 -*-
"""s326 — el clasificador batch de preguntas: el núcleo puro, sin red.

Lo que este fichero fija:
  1. la taxonomía VIGENTE carga, tiene `otros`, sus reglas apuntan dentro, y
     lleva las adjudicaciones de la v2 (dos fusiones + «no es una pregunta»);
  2. el parser del LLM es ESTRICTO: categoría fuera de lista = respuesta
     descartada ENTERA (jamás degradada a 'otros' — 'otros' es una elección
     del clasificador, no su modo de fallo);
  3. marcas: índice canónico con desambiguación, escaneo con límite de
     palabra, y canonicalización de las menciones del LLM (lo que resuelve se
     muda a `marcas`; solo lo desconocido queda libre);
  4. `clasificar_fila`: la ruta por regla NO llama al LLM; sin LLM la fila
     queda pendiente (None), nunca a medias;
  5. el payload escribe EXACTAMENTE las columnas que la 021 concede (la clase
     de fallo 9-bis — columna escrita sin GRANT — muere aquí, no en producción).
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from src import clasificacion as cl

RAIZ = Path(__file__).resolve().parent.parent
M021 = (RAIZ / "migrations" / "021_query_clasificacion.sql").read_text("utf-8")
#: La migración que define el CHECK de `categoria` VIGENTE. Al subir la
#: taxonomía se apunta aquí a su migración hermana — fricción deliberada,
#: igual que el censo de módulos: un cambio de categorías paga un toque.
M_TAXONOMIA = (RAIZ / "migrations" / "022_taxonomia_v2.sql").read_text("utf-8")

TAX = cl.cargar_taxonomia()


# ------------------------------------------------------------------ taxonomía


def test_taxonomia_vigente_carga_y_es_coherente():
    assert TAX.version == 6
    assert "otros" in TAX.ids
    assert len(TAX.ids) == len(set(TAX.ids)) == 8
    assert TAX.regla_rutas["catalog_shortcut"] == "catalogo_especificaciones"
    assert set(TAX.regla_rutas.values()) <= set(TAX.ids)


#: sha256 del CONTENIDO SEMÁNTICO de la taxonomía (ids + descripciones +
#: reglas) por versión. Existe porque el contrato «cualquier cambio sube
#: `version`» era SOLO PROSA (hallazgo Sol s326b): los tests fijaban los ids y
#: el número, así que reescribir una descripción —que ES el prompt, y cambia
#: las asignaciones— dejaba todo verde y las filas históricas sin re-encolar.
#: Al subir de versión se añade la entrada nueva aquí, y la vieja se queda como
#: traza de qué clasificó cada número.
HUELLAS_TAXONOMIA = {
    5: "6d29f56b581f0a34",
    6: "512bf3108860f4d2",
}


def _huella(tax) -> str:
    import hashlib
    canon = "\n".join(
        [str(tax.version)]
        + [f"{cid}|{desc}" for cid, desc in tax.categorias]
        + [f"{k}={v}" for k, v in sorted(tax.regla_rutas.items())])
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()[:16]


def test_cambiar_una_descripcion_obliga_a_subir_la_version():
    esperada = HUELLAS_TAXONOMIA.get(TAX.version)
    assert esperada is not None, (
        f"taxonomía v{TAX.version} sin huella declarada: añade su entrada a "
        f"HUELLAS_TAXONOMIA (la de ahora es {_huella(TAX)!r})")
    assert _huella(TAX) == esperada, (
        f"el contenido de la taxonomía cambió SIN subir `version` (huella "
        f"{_huella(TAX)!r} ≠ {esperada!r}). Las descripciones SON el prompt: "
        f"cambiarlas cambia las asignaciones, así que exigen versión nueva — "
        f"si no, las filas ya clasificadas no se re-encolan y el histórico "
        f"queda mezclando dos criterios bajo el mismo número.")


def test_las_adjudicaciones_de_la_v2_estan_en_la_lista():
    """Las cuatro decisiones de Alberto que CAMBIAN la lista (19-ago): dos
    fusiones, la clase «no es una pregunta» y la retirada de los ids viejos."""
    assert "catalogo_especificaciones" in TAX.ids      # catálogo + specs
    assert "instalacion_configuracion" in TAX.ids      # instalación + config
    assert "no_es_pregunta" in TAX.ids                 # punto 7
    for retirado in ("especificaciones", "catalogo_documentacion",
                     "instalacion_cableado", "configuracion_programacion"):
        assert retirado not in TAX.ids, retirado


def test_prompt_lleva_las_categorias_y_la_pregunta_acotada():
    prompt = cl.construir_prompt(TAX, "¿Cómo se rearma la CAD-150? " + "x" * 5000)
    for cid, _ in TAX.categorias:
        assert f"- {cid}:" in prompt
    assert "¿Cómo se rearma la CAD-150?" in prompt
    assert len(prompt) < 6000  # la pregunta viaja recortada a 1500


# --------------------------------------------------------------------- parser


@pytest.mark.parametrize("crudo", [
    "",
    "no es json",
    '{"categoria": "inventada", "marcas_mencionadas": []}',   # fuera de lista
    '{"marcas_mencionadas": ["detnov"]}',                      # sin categoría
    '["averias_diagnostico"]',                                 # forma equivocada
])
def test_parser_estricto_descarta_entero(crudo):
    assert cl.parsear_respuesta(crudo, TAX.ids) is None


def test_parser_acepta_json_con_ruido_alrededor_y_normaliza_marcas():
    crudo = ('Claro, aquí tienes:\n'
             '{"categoria": "averias_diagnostico", '
             '"marcas_mencionadas": ["Détnov", "detnov", "X" , '
             '"<script>alert(1)</script>", "a", "m1", "m2", "m3", "m4"]}\n')
    categoria, marcas = cl.parsear_respuesta(crudo, TAX.ids)
    assert categoria == "averias_diagnostico"
    # tildes fuera, duplicados fuera, charset raro fuera, y el tope de 5 se
    # aplica ANTES de filtrar (m1..m4 ni se miran)
    assert marcas == ["detnov"]


# --------------------------------------------------------------------- marcas


NOMBRES = ["Detnov", "Morley-IAS", "Notifier", "Kidde", "Aguilera"]


def test_indice_incluye_primer_segmento_y_desambigua():
    indice = cl.indice_de_marcas(NOMBRES + ["Morley-Viejo"])
    assert indice["detnov"] == "Detnov"
    assert indice["morley-ias"] == "Morley-IAS"
    # «morley» apuntaría a dos marcas distintas → se descarta, no se adivina
    assert "morley" not in indice
    indice_solo = cl.indice_de_marcas(NOMBRES)
    assert indice_solo["morley"] == "Morley-IAS"


def test_escaneo_respeta_limites_de_palabra():
    indice = cl.indice_de_marcas(NOMBRES)
    assert cl.escanear_marcas("la central de KIDDE está en fallo", indice) == ["Kidde"]
    assert cl.escanear_marcas("¿qué es un morley?", indice) == ["Morley-IAS"]
    assert cl.escanear_marcas("un notifierx cualquiera", indice) == []
    assert cl.escanear_marcas("", indice) == []


def test_canonicalizar_libres_muda_lo_que_resuelve():
    indice = cl.indice_de_marcas(NOMBRES)
    resolver = {"noti": "Notifier"}.get
    canonicas, libres = cl.canonicalizar_libres(
        ["noti", "detnov", "marcarara"], indice,
        lambda m: resolver(m) or m)
    assert canonicas == ["Detnov", "Notifier"]
    assert libres == ["marcarara"]


# ------------------------------------------------------------- clasificar_fila


def _fila(**extra):
    base = {"id": "00000000-0000-0000-0000-000000000001",
            "query": "¿Qué fabricantes tienes?", "route": "catalog_shortcut",
            "source": "text", "product_models": []}
    base.update(extra)
    return base


def _marca_de_modelo(modelo):
    return {"CAD-250": "Detnov"}.get(modelo)


def test_ruta_por_regla_no_llama_al_llm():
    def _llm_prohibido(_prompt):
        raise AssertionError("la ruta por regla no puede pagar un LLM")

    clasif = cl.clasificar_fila(
        _fila(), TAX, cl.indice_de_marcas(NOMBRES),
        marca_de_modelo=_marca_de_modelo, resolver_alias=lambda m: m,
        llm=_llm_prohibido, modelo_llm="haiku")
    assert clasif["categoria"] == "catalogo_especificaciones"
    assert clasif["origen"] == "regla"
    assert clasif["modelo_llm"] is None
    assert clasif["taxonomia_version"] == TAX.version


def test_fila_rag_sin_llm_queda_pendiente():
    assert cl.clasificar_fila(
        _fila(route="rag"), TAX, {}, marca_de_modelo=_marca_de_modelo,
        resolver_alias=lambda m: m, llm=None, modelo_llm="haiku") is None


def test_fila_rag_con_llm_une_marcas_de_modelo_texto_y_llm():
    def _llm(_prompt):
        return ('{"categoria": "averias_diagnostico", '
                '"marcas_mencionadas": ["aguilera", "fantasma"]}')

    clasif = cl.clasificar_fila(
        _fila(route="rag", query="fallo de tierra en la kidde 2X",
              product_models=["cad-250"]),
        TAX, cl.indice_de_marcas(NOMBRES), marca_de_modelo=_marca_de_modelo,
        resolver_alias=lambda m: m, llm=_llm, modelo_llm="haiku")
    assert clasif["categoria"] == "averias_diagnostico"
    assert clasif["origen"] == "llm" and clasif["modelo_llm"] == "haiku"
    assert clasif["modelos"] == ["CAD-250"]
    assert clasif["marcas"] == ["Aguilera", "Detnov", "Kidde"]
    assert clasif["marcas_libres"] == ["fantasma"]


def test_respuesta_invalida_del_llm_deja_la_fila_pendiente():
    assert cl.clasificar_fila(
        _fila(route="rag"), TAX, {}, marca_de_modelo=_marca_de_modelo,
        resolver_alias=lambda m: m, llm=lambda _p: "categoria: otros",
        modelo_llm="haiku") is None


def test_ruta_null_cuenta_como_rag():
    clasif = cl.clasificar_fila(
        _fila(route=None), TAX, {}, marca_de_modelo=_marca_de_modelo,
        resolver_alias=lambda m: m,
        llm=lambda _p: '{"categoria": "otros", "marcas_mencionadas": []}',
        modelo_llm="haiku")
    assert clasif["origen"] == "llm"


# -------------------------------------------------------- pendientes y payload


@pytest.mark.parametrize("embed,esperado", [
    (None, True),
    ([], True),
    ({"taxonomia_version": TAX.version - 1} if TAX.version > 1 else
     {"taxonomia_version": 0}, True),
    ({"taxonomia_version": TAX.version}, False),
    ([{"taxonomia_version": TAX.version}], False),
    ({"taxonomia_version": "basura"}, True),
])
def test_es_pendiente_acepta_las_tres_formas_del_embed(embed, esperado):
    assert cl.es_pendiente({"query_clasificacion": embed}, TAX.version) is esperado


def test_el_payload_escribe_exactamente_las_columnas_concedidas_en_021():
    """La clase 9-bis (columna escrita sin GRANT) muere aquí: cada clave del
    payload tiene que estar en el GRANT INSERT de la migración, y al revés."""
    clasif = cl.clasificar_fila(
        _fila(), TAX, {}, marca_de_modelo=_marca_de_modelo,
        resolver_alias=lambda m: m, llm=None, modelo_llm="haiku")
    grant = re.search(
        r"GRANT INSERT \(([^)]+)\)\s+ON public\.query_clasificacion",
        re.sub(r"\s+", " ", M021))
    assert grant, "la 021 tiene que conceder INSERT por columnas"
    columnas = {c.strip() for c in grant.group(1).split(",")}
    assert set(clasif) == columnas


def test_el_check_vigente_en_sql_es_la_taxonomia_del_yaml():
    """Las dos mitades del contrato, atadas: la lista del YAML y el CHECK de la
    base tienen que decir EXACTAMENTE lo mismo (si divergen, el job escribe
    categorías que la base rechaza — o al revés, y nadie se entera hasta
    producción)."""
    check = re.search(
        r"ADD CONSTRAINT query_clasificacion_categoria_check "
        r"CHECK \(categoria IN \(([^)]+)\)\)",
        re.sub(r"\s+", " ", M_TAXONOMIA))
    assert check, "falta el CHECK de categoria en la migración de taxonomía"
    en_sql = {c.strip().strip("'") for c in check.group(1).split(",")}
    assert en_sql == set(TAX.ids), (
        "taxonomía YAML ≠ CHECK vigente — una taxonomía nueva exige migración "
        "hermana (contrato del YAML)")


def test_la_migracion_de_taxonomia_retira_los_ids_viejos_de_datos_y_check():
    """El mapa de la 022 no puede dejar filas con un id que el CHECK ya no
    admite: la migración comprueba AMBOS lados (postcondición propia)."""
    compacta = re.sub(r"\s+", " ", M_TAXONOMIA)
    for retirado in ("especificaciones", "catalogo_documentacion",
                     "instalacion_cableado", "configuracion_programacion"):
        assert f"WHEN '{retirado}'" in compacta, f"{retirado} sin mapa"
    assert "quedan % filas con el id retirado" in compacta
    assert "el CHECK todavía admite el id retirado" in compacta


# ------------------------------------------------------------ correr_pendientes


def test_correr_pendientes_cuenta_sin_escribir(monkeypatch):
    filas = [
        _fila(),                                   # regla
        _fila(id="00000000-0000-0000-0000-000000000002", route="rag"),  # sin llm
    ]
    monkeypatch.setattr(cl, "leer_pendientes", lambda version, cap: filas)

    def _prohibido(_nuevas, _existentes=None):
        raise AssertionError("dry_run no escribe")

    monkeypatch.setattr(cl, "escribir_clasificaciones", _prohibido)
    catalogo = cl.Catalogo(nombres=NOMBRES,
                           marca_de_modelo=_marca_de_modelo,
                           resolver_alias=lambda m: m)

    recibo = cl.correr_pendientes(cap=10, catalogo=catalogo, api_key=None,
                                  dry_run=True)
    assert recibo["examinadas"] == 2
    assert recibo["por_regla"] == 1
    assert recibo["sin_llm"] == 1
    assert recibo["escritas"] == 0 and recibo["dry_run"] is True


def test_las_ya_clasificadas_van_por_update_y_las_nuevas_por_insert(monkeypatch):
    """Incidente del backfill (19-ago): el upsert merge-duplicates de PostgREST
    re-escribe la PK y el GRANT lo prohíbe (trinquete del gate ACL). El verbo
    lo decide la marca de `leer_pendientes`: nueva→INSERT, ya-clasificada→PATCH
    (payload SIN query_log_id — eso lo garantiza escribir_clasificaciones)."""
    filas = [
        _fila(),
        _fila(id="00000000-0000-0000-0000-000000000002",
              **{"_ya_clasificada": True}),
    ]
    monkeypatch.setattr(cl, "leer_pendientes", lambda version, cap: filas)
    capturado = {}

    def _doble(nuevas, existentes=None):
        capturado["nuevas"] = nuevas
        capturado["existentes"] = existentes or []
        return len(nuevas) + len(existentes or [])

    monkeypatch.setattr(cl, "escribir_clasificaciones", _doble)
    catalogo = cl.Catalogo(nombres=NOMBRES,
                           marca_de_modelo=_marca_de_modelo,
                           resolver_alias=lambda m: m)
    recibo = cl.correr_pendientes(cap=10, catalogo=catalogo, api_key=None)
    assert recibo["escritas"] == 2
    assert [f["query_log_id"] for f in capturado["nuevas"]] == \
        ["00000000-0000-0000-0000-000000000001"]
    assert [f["query_log_id"] for f in capturado["existentes"]] == \
        ["00000000-0000-0000-0000-000000000002"]
    # la marca interna jamás viaja en el payload
    assert all("_ya_clasificada" not in f
               for f in capturado["nuevas"] + capturado["existentes"])


def test_aplanar_vieja_acepta_objeto_lista_y_nada():
    padre = {"id": "x", "query": "q", "route": "rag"}
    assert cl.aplanar_vieja({"query_logs": padre}) == padre
    assert cl.aplanar_vieja({"query_logs": [padre]}) == padre
    assert cl.aplanar_vieja({"query_logs": []}) is None
    assert cl.aplanar_vieja({}) is None


def test_el_modulo_de_clasificacion_es_raiz_pura():
    """La frontera del import contract, fijada donde nace: `src/clasificacion`
    NO importa rag/orchestrator/bot — el catálogo entra inyectado (Catalogo)."""
    import ast
    from pathlib import Path

    arbol = ast.parse((Path(cl.__file__)).read_text("utf-8"))
    importados = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.ImportFrom) and nodo.level:
            importados.add((nodo.module or "").split(".")[0])
    assert not importados & {"rag", "orchestrator", "bot"}, importados
