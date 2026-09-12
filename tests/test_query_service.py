from datetime import datetime, timedelta

import pytest
from app.models.categorias import CategoriaGasto
from app.models.gasto import Gasto
from app.schemas.gasto_schema import ConsultaGasto, PeriodoConsulta, TipoConsulta
from app.services import query_service
from app.services.date_utils import TZ_LOCAL
from app.services.query_service import (
    _normalizar_manteniendo_espacios,
    _normalizar_texto,
    _rango_por_periodo,
    buscar_total_por_descripcion,
    responder_consulta,
)

# Un instante fijo en hora local: miercoles 16 de septiembre de 2026, 10:30.
AHORA_FIJA = datetime(2026, 9, 16, 10, 30, tzinfo=TZ_LOCAL)


class _RelojFijo(datetime):
    @classmethod
    def now(cls, tz=None):
        return AHORA_FIJA if tz is None else AHORA_FIJA.astimezone(tz)


@pytest.fixture
def reloj_fijo(monkeypatch):
    """Congela datetime.now() dentro de query_service."""
    monkeypatch.setattr(query_service, "datetime", _RelojFijo)


def _utc(anio, mes, dia, hora=0):
    """Medianoche local (UTC-4) expresada como datetime naive en UTC."""
    return datetime(anio, mes, dia, hora) + timedelta(hours=4)


def _agregar_gasto(db, usuario, monto, categoria, descripcion, fecha):
    gasto = Gasto(
        usuario_id=usuario.id, monto=monto, categoria=categoria,
        descripcion=descripcion, fecha=fecha,
    )
    db.add(gasto)
    db.commit()
    return gasto


# --- Normalizacion de texto ---

def test_normalizar_texto_quita_acentos_espacios_y_signos():
    assert _normalizar_texto("  Préstamo BHD-2! ") == "prestamobhd2"


def test_normalizar_manteniendo_espacios_conserva_espacios_y_signos():
    # El "¿" no es ASCII, asi que se pierde; el "?" y el espacio se quedan.
    assert _normalizar_manteniendo_espacios(" ¿Qué GASTÉ? ") == "que gaste?"


# --- Rangos de fechas ---

@pytest.mark.parametrize("periodo, inicio, fin, etiqueta", [
    (PeriodoConsulta.HOY, _utc(2026, 9, 16), _utc(2026, 9, 17), "hoy"),
    (PeriodoConsulta.AYER, _utc(2026, 9, 15), _utc(2026, 9, 16), "ayer"),
    (PeriodoConsulta.ESTA_SEMANA, _utc(2026, 9, 14), _utc(2026, 9, 21), "esta semana"),
    (PeriodoConsulta.SEMANA_PASADA, _utc(2026, 9, 7), _utc(2026, 9, 14), "la semana pasada"),
    (PeriodoConsulta.ESTE_MES, _utc(2026, 9, 1), _utc(2026, 10, 1), "este mes"),
    (PeriodoConsulta.MES_PASADO, _utc(2026, 8, 1), _utc(2026, 9, 1), "el mes pasado"),
])
def test_rango_por_periodo(reloj_fijo, periodo, inicio, fin, etiqueta):
    assert _rango_por_periodo(periodo) == (inicio, fin, etiqueta)


def test_este_mes_en_diciembre_termina_en_enero(monkeypatch):
    class _Diciembre(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 12, 20, 9, tzinfo=TZ_LOCAL)

    monkeypatch.setattr(query_service, "datetime", _Diciembre)

    inicio, fin, _ = _rango_por_periodo(PeriodoConsulta.ESTE_MES)

    assert (inicio, fin) == (_utc(2026, 12, 1), _utc(2027, 1, 1))


# --- Consultas contra la base ---

def test_total_general_solo_cuenta_el_periodo_y_el_usuario(db, usuario, reloj_fijo):
    from app.repositories.usuario_repository import crear_usuario
    otro = crear_usuario(db, nombre="Luis", numero_whatsapp="18090000000")

    _agregar_gasto(db, usuario, 100, CategoriaGasto.COMIDA, "almuerzo", _utc(2026, 9, 10, 12))
    _agregar_gasto(db, usuario, 50, CategoriaGasto.PASAJE, "uber", _utc(2026, 9, 16, 8))
    _agregar_gasto(db, usuario, 999, CategoriaGasto.COMIDA, "mes pasado", _utc(2026, 8, 31, 12))
    _agregar_gasto(db, otro, 777, CategoriaGasto.COMIDA, "de otro usuario", _utc(2026, 9, 10, 12))

    consulta = ConsultaGasto(tipo=TipoConsulta.TOTAL_GENERAL)

    assert responder_consulta(db, usuario.id, consulta) == "Tu gasto total este mes: *RD$150.00*"


def test_total_por_categoria(db, usuario, reloj_fijo):
    _agregar_gasto(db, usuario, 1200.5, CategoriaGasto.COMIDA, "super", _utc(2026, 9, 2, 12))
    _agregar_gasto(db, usuario, 300, CategoriaGasto.SALUD, "farmacia", _utc(2026, 9, 3, 12))

    consulta = ConsultaGasto(tipo=TipoConsulta.POR_CATEGORIA, categoria=CategoriaGasto.COMIDA)

    assert responder_consulta(db, usuario.id, consulta) == "Gastaste *RD$1,200.50* en comida este mes"


def test_por_categoria_sin_categoria_pide_aclaracion(db, usuario, reloj_fijo):
    consulta = ConsultaGasto(tipo=TipoConsulta.POR_CATEGORIA)

    assert "No entendí qué categoría" in responder_consulta(db, usuario.id, consulta)


def test_desglose_agrupa_por_categoria(db, usuario, reloj_fijo):
    _agregar_gasto(db, usuario, 100, CategoriaGasto.COMIDA, "a", _utc(2026, 9, 2, 12))
    _agregar_gasto(db, usuario, 150, CategoriaGasto.COMIDA, "b", _utc(2026, 9, 3, 12))
    _agregar_gasto(db, usuario, 40, CategoriaGasto.PASAJE, "c", _utc(2026, 9, 4, 12))

    respuesta = responder_consulta(db, usuario.id, ConsultaGasto(tipo=TipoConsulta.DESGLOSE))

    assert "•comida: *RD$250.00*" in respuesta
    assert "•pasaje: *RD$40.00*" in respuesta
    assert respuesta.endswith("Total: *RD$290.00*")


def test_desglose_sin_gastos(db, usuario, reloj_fijo):
    respuesta = responder_consulta(db, usuario.id, ConsultaGasto(tipo=TipoConsulta.DESGLOSE))

    assert respuesta == "No tienes gastos registrados este mes"


def test_desglose_categoria_muestra_fecha_local(db, usuario, reloj_fijo):
    # 02:00 UTC del dia 5 todavia es el dia 4 en RD (UTC-4).
    _agregar_gasto(db, usuario, 80, CategoriaGasto.SALUD, "farmacia", datetime(2026, 9, 5, 2))

    consulta = ConsultaGasto(tipo=TipoConsulta.DESGLOSE_CATEGORIA, categoria=CategoriaGasto.SALUD)
    respuesta = responder_consulta(db, usuario.id, consulta)

    assert "• *04/09/2026*: RD$80.00 - _farmacia_" in respuesta
    assert respuesta.endswith("Total: *RD$80.00*")


def test_dia_especifico_filtra_solo_ese_dia(db, usuario, reloj_fijo):
    _agregar_gasto(db, usuario, 60, CategoriaGasto.COMIDA, "dia 10", _utc(2026, 9, 10, 12))
    _agregar_gasto(db, usuario, 90, CategoriaGasto.COMIDA, "dia 11", _utc(2026, 9, 11, 12))

    consulta = ConsultaGasto(tipo=TipoConsulta.TOTAL_GENERAL, dia_especifico=10)

    assert responder_consulta(db, usuario.id, consulta) == "Tu gasto total el 10 de este mes: *RD$60.00*"


def test_dia_que_no_existe_en_el_mes(db, usuario, reloj_fijo):
    # Septiembre no tiene dia 31.
    consulta = ConsultaGasto(tipo=TipoConsulta.TOTAL_GENERAL, dia_especifico=31)

    respuesta = responder_consulta(db, usuario.id, consulta)

    assert respuesta == "No pude calcular esa fecha: el dia 31 no existe en el mes actual"


def test_buscar_total_por_descripcion_ignora_acentos(db, usuario, reloj_fijo):
    _agregar_gasto(db, usuario, 500, CategoriaGasto.PAGOS, "Préstamo BHD", _utc(2026, 9, 5, 12))
    _agregar_gasto(db, usuario, 200, CategoriaGasto.COMIDA, "pizza", _utc(2026, 9, 6, 12))

    total, etiqueta, coincidencias = buscar_total_por_descripcion(db, usuario.id, "prestamo")

    assert total == 500
    assert etiqueta == "este mes"
    assert [g.descripcion for g in coincidencias] == ["Préstamo BHD"]


def test_buscar_total_por_descripcion_sin_coincidencias(db, usuario, reloj_fijo):
    assert buscar_total_por_descripcion(db, usuario.id, "netflix") is None
