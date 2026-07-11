import re
from sqlalchemy.orm import Session
from app.repositories.usuario_repository import crear_usuario, obtener_usuario_por_numero
from app.repositories.gasto_repository import crear_gasto
from app.repositories.gasto_fijo_repository import crear_gasto_fijo
from app.services.gasto_fijo_service import responder_gasto_fijo
from app.services.date_utils import calcular_proxima_fecha, dias_restantes
from app.integrations.groq_client import (
    extraer_gasto, 
    extraer_consulta, 
    extraer_gastos,
    extraer_gasto_fijo,
    extraer_consulta_gasto_fijo
        )
from app.services.intent_router import detectar_intenciones, detectar_categoria_directa, Intencion
from app.services.query_service import responder_consulta, buscar_total_por_descripcion, _normalizar_manteniendo_espacios
from app.schemas.gasto_schema import ConsultaGasto, TipoConsulta, PeriodoConsulta
from app.models.usuarios import Usuario
from app.models.gasto import Gasto

def _resolver_usuario(db: Session, numero_whatsapp: str, nombre: str) -> Usuario:
    usuario = obtener_usuario_por_numero(db, numero_whatsapp)
    if usuario is None:
        usuario = crear_usuario(db, nombre=nombre, numero_whatsapp=numero_whatsapp)
    return usuario

def _formatear_confirmacion(gasto: Gasto) -> str:
    return (
        f"✅ Gasto registrado: *RD${gasto.monto}* en {gasto.categoria.value} "
        f"({gasto.descripcion})"
    )

def _formatear_confirmacion_fijo(gf) -> str:
    fecha = calcular_proxima_fecha(gf.dia_mes)
    dias = dias_restantes(gf.dia_mes)
    return (
        f"📍 Pago fijo registrado: *RD${float(gf.monto):,.2f}* - {gf.descripcion} "
        f"({gf.categoria.value})\n"
        f"Se paga el *{gf.dia_mes} de cada mes*."
        f"Próximo: {fecha.strftime('%d/%m/%Y')} (faltan {dias} días)."
    )

def procesar_mensaje(db: Session, numero_whatsapp: str, texto: str, nombre: str = "Usuario") -> str:
    usuario = _resolver_usuario(db, numero_whatsapp, nombre)
    categoria_directa = detectar_categoria_directa(texto)
    if categoria_directa is not None:
        consulta = ConsultaGasto(tipo=TipoConsulta.POR_CATEGORIA, categoria=categoria_directa, periodo=PeriodoConsulta.ESTE_MES)
        return responder_consulta(db, usuario.id, consulta)

    intenciones = detectar_intenciones(texto)
    partes = []

    if Intencion.SALUDO in intenciones:
        partes.append("Hola! Como te ayudo hoy?")

    if Intencion.REGISTRAR_GASTO_FIJO in intenciones:
        try: 
            extraccion = extraer_gasto_fijo(texto)
        except Exception:
            return "No pude entender ese pago fijo. Intenta algo como 'Netflix RD$500 el 12 de cada mes'"
        
        gasto_fijo = crear_gasto_fijo(
            db,
            usuario_id=usuario.id,
            monto=extraccion.monto,
            categoria=extraccion.categoria,
            descripcion=extraccion.descripcion,
            dia_mes=extraccion.dia_mes
        )
        partes.append(_formatear_confirmacion_fijo(gasto_fijo))
        return "\n".join(partes)

    if Intencion.PREGUNTA_GASTO_FIJO in intenciones:
        consulta_fijo = extraer_consulta_gasto_fijo(texto)
        partes.append(responder_gasto_fijo(
            db,
            usuario.id,
            termino=consulta_fijo.termino,
            categoria=consulta_fijo.categoria,
            )
        )
        return "\n".join(partes)

    if Intencion.REGISTRAR_GASTO in intenciones and Intencion.PREGUNTA not in intenciones:

        for extraccion in extraer_gastos(texto):
            if extraccion.monto is None:
                partes.append("⚠️ No pude identificar el monto de uno de los gastos")
            else:
                gasto = crear_gasto(
                    db,
                    usuario_id=usuario.id,
                    monto = extraccion.monto,
                    categoria=extraccion.categoria,
                    descripcion=extraccion.descripcion
                )
                partes.append(_formatear_confirmacion(gasto))        

    if Intencion.REGISTRAR_GASTO in intenciones and Intencion.PREGUNTA in intenciones:
        
        for extraccion in extraer_gastos(texto):
            if extraccion.monto is None:
                partes.append("⚠️ No pude identificar el monto de uno de los gastos")
            else:
                gasto = crear_gasto(
                    db,
                    usuario_id=usuario.id,
                    monto = extraccion.monto,
                    categoria=extraccion.categoria,
                    descripcion=extraccion.descripcion
                )
                partes.append(_formatear_confirmacion(gasto))  

        consulta = extraer_consulta(texto)
        texto_normalizado = _normalizar_manteniendo_espacios(texto)
        if consulta.categoria is not None and (re.search(r"\bque\b", texto_normalizado) or any(p in texto_normalizado for p in ["desglos", "detall"])):
            consulta.tipo = TipoConsulta.DESGLOSE_CATEGORIA
        partes.append(responder_consulta(db, usuario.id, consulta))

    # PREGUNTA sola (sin gasto)
    elif Intencion.PREGUNTA in intenciones and Intencion.REGISTRAR_GASTO not in intenciones:
        consulta = extraer_consulta(texto)
        texto_normalizado = _normalizar_manteniendo_espacios(texto)
        if consulta.categoria is not None and (re.search(r"\bque\b", texto_normalizado) or any(p in texto_normalizado for p in ["desglos", "detall"])):
            consulta.tipo = TipoConsulta.DESGLOSE_CATEGORIA
        partes.append(responder_consulta(db, usuario.id, consulta))

    # Si solo hay SALUDO sin gasto ni pregunta
    if not partes:
        resultado_busqueda = buscar_total_por_descripcion(db, usuario.id, texto)
        if resultado_busqueda is not None:
            total, etiqueta, coincidencias = resultado_busqueda
            partes.append(
                f"Gastaste *RD${total:,.2f}* en: "
                f"\"{texto.strip()}\" {etiqueta}"
                )
        else:
            partes.append("👋 ¡Hola! Puedo registrar tus gastos o responder preguntas como '¿cuánto gasté en comida este mes?'")

    return "\n".join(partes)