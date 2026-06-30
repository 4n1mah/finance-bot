# 💸 Finance Bot — WhatsApp Personal Finance Tracker

Bot de WhatsApp para registrar gastos personales mediante lenguaje natural. Proyecto de portafolio construido con Python y FastAPI.

> "Gasté 350 en uber al trabajo" → el bot extrae el monto, la categoría y la descripción, y los guarda automáticamente en la base de datos.

---

## ¿Qué hace?

El usuario le escribe al bot por WhatsApp en texto libre — sin formularios, sin comandos. El bot entiende el mensaje, extrae los datos del gasto, los persiste en PostgreSQL y confirma al usuario con un mensaje de vuelta.

**V1 (actual):** registro de gastos  
**V1.1 (próximo):** responder preguntas como "¿cuánto gasté en comida este mes?"

---

## Stack

| Capa | Tecnología |
|---|---|
| API | Python + FastAPI |
| LLM | Groq (llama-3.3-70b-versatile) |
| Base de datos | PostgreSQL en Neon |
| Deploy | Railway |
| Mensajería | Meta WhatsApp Business API |

---

## Arquitectura

```
app/
├── core/           # Configuración y conexión a base de datos
├── models/         # Modelos SQLAlchemy (Usuario, Gasto)
├── schemas/        # Modelos Pydantic para validación
├── repositories/   # Queries a la base de datos
├── services/       # Lógica de negocio (intent router, expense service)
├── integrations/   # Clientes externos (Groq, WhatsApp)
└── routers/        # Endpoints FastAPI (webhook)
```

**Principio de diseño clave:** el LLM actúa como capa de interpretación delgada — extrae intención estructurada del texto libre, pero nunca genera ni ejecuta SQL. Python construye todas las queries. Esto mantiene el sistema predecible y auditable.

**Flujo completo:**

```
WhatsApp → Meta API → webhook.py → intent_router → expense_service → Groq → repository → Neon
                                                                          ↓
                                                                   WhatsApp (respuesta)
```

### Intent Router
Reglas léxicas simples (sin ML) para distinguir mensajes de registro de gastos vs preguntas. La decisión es barata (microsegundos, sin costo de API) y reserva el LLM para lo que sí justifica su uso: extraer monto, categoría y descripción de texto libre.

### Categorías de gasto
Enum cerrado: `Comida`, `Pasaje`, `Cuidado Personal`, `Servicios`, `Salud`, `Salidas`, `Ahorros`, `Pedidos`, `Pagos`, `Otros`.

---

## Variables de entorno

```env
DATABASE_URL=
GROQ_API_KEY=
META_VERIFY_TOKEN=
META_ACCESS_TOKEN=
META_PHONE_NUMBER_ID=
```

---

## Instalación local

```bash
git clone https://github.com/tu-usuario/finance-bot.git
cd finance-bot
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```

---

## Deploy

El proyecto incluye un `Procfile` para Railway:

```
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Las variables de entorno se configuran directamente en el panel de Railway (el `.env` nunca se sube al repositorio).
