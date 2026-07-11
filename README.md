# Finance Bot — WhatsApp Personal Finance Tracker

Bot de WhatsApp para registrar y consultar gastos personales mediante lenguaje natural. Proyecto de portafolio construido con Python y FastAPI.

> "Gasté 350 en uber al trabajo" → el bot extrae el monto, la categoría y la descripción, y los guarda automáticamente en la base de datos.

---

## ¿Qué hace?

El usuario le escribe al bot por WhatsApp en texto libre — sin formularios, sin comandos. El bot entiende el mensaje, extrae los datos, los persiste en PostgreSQL y confirma al usuario con un mensaje de vuelta.

**Funcionalidades actuales:**

- **Registro de gastos:** "Gasté 350 en uber al trabajo" → monto, categoría y descripción extraídos y guardados. Soporta varios gastos en un solo mensaje.
- **Consultas:** "¿Cuánto gasté en comida este mes?", "dame un resumen de la semana pasada", "desglósame mis gastos de salud" → totales generales, por categoría o desglose detallado, con soporte de períodos (hoy, ayer, esta semana, semana pasada, este mes, mes pasado) y días específicos ("¿cuánto gasté el 15?").
- **Gastos fijos:** "Netflix los 12 de cada mes por 400" → registra pagos recurrentes; "¿cuándo pago el préstamo del BHD?" o "¿cuáles son mis pagos fijos?" → responde con la próxima fecha de cobro y los días restantes.
- **Mensajes combinados:** el intent router detecta múltiples intenciones en un mismo mensaje ("Hola, gasté 200 en comida. ¿Cuánto llevo gastado?").

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
├── core/           # Configuración (pydantic-settings) y conexión a base de datos
├── models/         # Modelos SQLAlchemy (Usuario, Gasto, GastoFijo)
├── schemas/        # Modelos Pydantic para validación
├── repositories/   # Queries a la base de datos (gastos, gastos fijos, usuarios)
├── services/       # Lógica de negocio (intent router, expense, query, gasto fijo, fechas)
├── integrations/   # Clientes externos (Groq, WhatsApp)
└── routers/        # Endpoints FastAPI (webhook)
```

**Principio de diseño clave:** el LLM actúa como capa de interpretación delgada — extrae intención estructurada del texto libre, pero nunca genera ni ejecuta SQL. Python construye todas las queries. Esto mantiene el sistema predecible y auditable.

**Flujo completo:**

```
WhatsApp → Meta API → webhook.py → intent_router → expense/query/gasto_fijo service → Groq → repository → Neon
                                                                                          ↓
                                                                                   WhatsApp (respuesta)
```

### Intent Router
Reglas léxicas simples (sin ML) para clasificar cada mensaje: registro de gasto, registro de gasto fijo, pregunta sobre gastos, pregunta sobre pagos fijos o saludo. Devuelve una **lista** de intenciones, así un solo mensaje puede disparar varias acciones. La decisión es barata (microsegundos, sin costo de API) y reserva el LLM para lo que sí justifica su uso: extraer monto, categoría, descripción, período o día de cobro del texto libre.

### Webhook
Además de recibir los mensajes de Meta, el webhook deduplica mensajes ya procesados (Meta reintenta entregas) y envía el indicador de "escribiendo…" mientras procesa.

### Categorías de gasto
Enum cerrado: `comida`, `pasaje`, `cuidado_personal`, `servicios`, `salud`, `salidas`, `ahorros`, `pedidos`, `pagos`, `otros`.

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
source venv/bin/activate     # Linux / macOS
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
