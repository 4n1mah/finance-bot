from app.core.database import SessionLocal
from app.repositories.usuario_repository import crear_usuario, obtener_usuario_por_numero
from app.repositories.gasto_repository import (
    crear_gasto,
    obtener_total_por_categoria,
    obtener_total_general,
    obtener_total_por_categoria_especifica,
    obtener_gastos_detalle,
)
from app.models.gasto import CategoriaGasto
from datetime import datetime, UTC

db = SessionLocal()

usuario_existente = obtener_usuario_por_numero(db, "18091234567")
if usuario_existente is None:
    usuario_prueba = crear_usuario(db, nombre="Sadiel", numero_whatsapp="18091234567")
    print("Usuario creado:", usuario_prueba.id, usuario_prueba.nombre)
else:
    usuario_prueba = usuario_existente
    print("Usuario ya existía:", usuario_prueba.id, usuario_prueba.nombre)

gasto_prueba = crear_gasto(
    db,
    usuario_id=usuario_prueba.id,
    monto=2700,
    categoria=CategoriaGasto.PASAJE,
    descripcion="gasolina"
)
print("Gasto creado:", gasto_prueba.id, gasto_prueba.monto, gasto_prueba.categoria)

inicio_mes = datetime.now(UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
ahora = datetime.now(UTC)

print("Por categoría:", obtener_total_por_categoria(db, usuario_prueba.id, inicio_mes, ahora))
print("Total general:", obtener_total_general(db, usuario_prueba.id, inicio_mes, ahora))
print("Usuario existente:", obtener_usuario_por_numero(db, "18091234567").nombre)
print("Total en pasaje:", obtener_total_por_categoria_especifica(db, usuario_prueba.id, CategoriaGasto.PASAJE, inicio_mes, ahora))
print("Detalle gastos:", obtener_gastos_detalle(db, usuario_prueba.id, inicio_mes, ahora))

db.close()