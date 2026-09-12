from datetime import date

import pytest
from app.models.categorias import CategoriaGasto
from app.repositories.gasto_fijo_repository import (
    crear_gasto_fijo,
    desactivar_gasto_fijo,
    obtener_activos,
)
from app.services import date_utils
from app.services.gasto_fijo_service import (
    _formatear_dias,
    buscar_gastos_fijos_por_descripcion,
    responder_gasto_fijo,
)


@pytest.fixture
def hoy_fijo(monkeypatch):
    """
    Congela 'hoy' en el 10 de septiembre de 2026. Se parchea date_utils porque
    ahi es donde calcular_proxima_fecha y dias_restantes miran el reloj.
    """
    monkeypatch.setattr(date_utils, "datetime", _reloj(date(2026, 9, 10)))


def _reloj(dia):
    from datetime import datetime

    class _Fijo(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(dia.year, dia.month, dia.day, 12, tzinfo=tz)

    return _Fijo


@pytest.mark.parametrize("dias, esperado", [
    (0, "*es hoy*"),
    (1, "falta *1 dia*"),
    (5, "faltan *5 dias*"),
])
def test_formatear_dias(dias, esperado):
    assert _formatear_dias(dias) == esperado


def test_desactivar_saca_el_gasto_de_los_activos(db, usuario):
    gf = crear_gasto_fijo(db, usuario.id, 500, CategoriaGasto.SERVICIOS, "Netflix", 12)

    desactivar_gasto_fijo(db, gf.id)

    assert obtener_activos(db, usuario.id) == []


def test_desactivar_id_inexistente_devuelve_none(db):
    assert desactivar_gasto_fijo(db, 999) is None


def test_buscar_por_descripcion_parcial_y_sin_acentos(db, usuario):
    crear_gasto_fijo(db, usuario.id, 8000, CategoriaGasto.PAGOS, "Préstamo BHD", 4)
    crear_gasto_fijo(db, usuario.id, 500, CategoriaGasto.SERVICIOS, "Netflix", 12)

    encontrados = buscar_gastos_fijos_por_descripcion(db, usuario.id, "bhd")

    assert [gf.descripcion for gf in encontrados] == ["Préstamo BHD"]


def test_responder_sin_pagos_fijos(db, usuario):
    assert responder_gasto_fijo(db, usuario.id) == "No tienes pagos fijos registrados todavia."


def test_responder_termino_sin_coincidencias(db, usuario):
    respuesta = responder_gasto_fijo(db, usuario.id, termino="spotify")

    assert respuesta == "No encontre ningun pago fijo que coincida con 'spotify'."


def test_responder_categoria_sin_pagos(db, usuario):
    respuesta = responder_gasto_fijo(db, usuario.id, categoria=CategoriaGasto.SALUD)

    assert respuesta == "No tienes pagos fijos registrados en salud."


@pytest.mark.usefixtures("hoy_fijo")
def test_responder_ordena_por_el_pago_mas_cercano(db, usuario):
    # Hoy es 10/09: el dia 4 ya paso (toca en octubre), el 12 es en 2 dias.
    crear_gasto_fijo(db, usuario.id, 8000, CategoriaGasto.PAGOS, "Prestamo BHD", 4)
    crear_gasto_fijo(db, usuario.id, 500, CategoriaGasto.SERVICIOS, "Netflix", 12)

    respuesta = responder_gasto_fijo(db, usuario.id)

    assert respuesta == (
        "📍 Todos tus pagos fijos:\n"
        "• _Netflix_: RD$500.00 el *12 de septiembre* (faltan *2 dias*)\n"
        "• _Prestamo BHD_: RD$8,000.00 el *4 de octubre* (faltan *24 dias*)\n"
        "\n"
        "Total mensual: *RD$8,500.00*"
    )


@pytest.mark.usefixtures("hoy_fijo")
def test_responder_por_categoria_filtra(db, usuario):
    crear_gasto_fijo(db, usuario.id, 8000, CategoriaGasto.PAGOS, "Prestamo BHD", 4)
    crear_gasto_fijo(db, usuario.id, 500, CategoriaGasto.SERVICIOS, "Netflix", 10)

    respuesta = responder_gasto_fijo(db, usuario.id, categoria=CategoriaGasto.SERVICIOS)

    assert respuesta.startswith("📍 Tus pagos fijos de servicios:")
    assert "Netflix" in respuesta and "(*es hoy*)" in respuesta
    assert "Prestamo" not in respuesta
