from app.core.database import SessionLocal
from app.services.expense_service import procesar_mensaje

db = SessionLocal()

# Número de prueba distinto al que ya usaste en test_db.py, para no
# mezclar resultados con el usuario "Sadiel" que ya creaste ahí.
NUMERO_PRUEBA = "18095557777"

# Caso 1: mensaje normal de gasto -> debería crear usuario + gasto
respuesta = procesar_mensaje(db, NUMERO_PRUEBA, "gasté 350 en uber al trabajo", nombre="Sadiel Prueba")
print("Caso 1 (registrar):", respuesta)

# Caso 2: mismo número otra vez -> usuario YA existe, solo debe crear el gasto
respuesta = procesar_mensaje(db, NUMERO_PRUEBA, "pagué 1200 de luz")
print("Caso 2 (usuario reutilizado):", respuesta)

# Caso 3: mensaje que el intent_router debería detectar como pregunta
respuesta = procesar_mensaje(db, NUMERO_PRUEBA, "¿cuánto gasté en comida este mes?")
print("Caso 3 (pregunta, sin tocar Groq):", respuesta)

db.close()