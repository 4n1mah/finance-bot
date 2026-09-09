# Finance Bot — WhatsApp Personal Finance Tracker

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?logo=postgresql&logoColor=white)
![Groq](https://img.shields.io/badge/Groq-llama--3.3--70b-F55036)

Bot de WhatsApp para registrar y consultar gastos personales mediante lenguaje natural. Proyecto de portafolio construido con Python y FastAPI.

> **"Gasté 350 en uber al trabajo"** → el bot extrae el monto, la categoría y la descripción, y los guarda automáticamente en la base de datos.

---

## Demo

> _(Pendiente: capturas o GIF de una conversación real con el bot.)_

---

## ¿Qué hace?

El usuario le escribe al bot por WhatsApp en texto libre — sin formularios, sin comandos. El bot entiende el mensaje, extrae los datos, los persiste en PostgreSQL y confirma al usuario con un mensaje de vuelta.

| Funcionalidad | Ejemplo de mensaje | Respuesta |
|---|---|---|
| **Registro de gastos** | `Gasté 350 en uber al trabajo` | ✅ Gasto registrado: *RD$350* en pasaje (uber al trabajo) |
| **Varios gastos a la vez** | `Gasté 200 en almuerzo y 150 en el pasaje` | Un registro y una confirmación por cada gasto |
| **Consultas por período** | `¿Cuánto gasté en comida este mes?` | Gastaste *RD$4,250.00* en comida este mes |
| **Desglose** | `Desglósame mis gastos de salud` | Lista línea por línea con fecha, monto y descripción + total |
| **Gastos fijos** | `Netflix los 12 de cada mes por 400` | 📍 Pago fijo registrado… Próximo: 12/10/2026 (faltan 3 días) |
| **Consulta de pagos fijos** | `¿Cuándo pago el préstamo del BHD?` | Próxima fecha de cobro y días restantes |
| **Mensajes combinados** | `Hola, gasté 200 en comida. ¿Cuánto llevo gastado?` | Saluda, registra el gasto y responde la pregunta |

**Períodos soportados:** hoy, ayer, esta semana, semana pasada, este mes, mes pasado y días puntuales (`¿cuánto gasté el 15?`).

---

## Stack

| Capa | Tecnología |
|---|---|
| API | Python + FastAPI |
| LLM | Groq (`llama-3.3-70b-versatile`) |
| ORM | SQLAlchemy 2.x |
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

**Principio de diseño clave:** el LLM actúa como capa de interpretación delgada — extrae intención estructurada del texto libre, pero **nunca genera ni ejecuta SQL**. Python construye todas las queries. Esto mantiene el sistema predecible y auditable.

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

### Gastos fijos
Se guardan como plantilla (`descripcion`, `monto`, `dia_mes`) y la próxima fecha de cobro se calcula en tiempo real. Si un pago cae el 31 y el mes tiene 30 días, el cobro se ajusta al último día del mes. Cancelar un pago fijo lo marca como inactivo en lugar de borrarlo, para no perder el historial.

### Categorías de gasto
Enum cerrado: `comida`, `pasaje`, `cuidado_personal`, `servicios`, `salud`, `salidas`, `ahorros`, `pedidos`, `pagos`, `otros`.

---

## Variables de entorno

Copia `.env.example` a `.env` y completa los valores:

| Variable | De dónde sale |
|---|---|
| `DATABASE_URL` | Cadena de conexión PostgreSQL (Neon) |
| `GROQ_API_KEY` | [console.groq.com](https://console.groq.com) |
| `META_VERIFY_TOKEN` | Cadena que tú inventas; debe coincidir con la del panel de Meta |
| `META_ACCESS_TOKEN` | Token de la app de WhatsApp Business en Meta for Developers |
| `META_PHONE_NUMBER_ID` | ID del número de prueba o producción en Meta |

---

## Instalación local

```bash
git clone https://github.com/4n1mah/finance-bot.git
cd finance-bot

python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Linux / macOS

pip install -r requirements.txt
cp .env.example .env         # y completa los valores

uvicorn app.main:app --reload
```

La API queda en `http://localhost:8000` y la documentación interactiva en `http://localhost:8000/docs`.

Para que Meta pueda llegar a tu máquina durante el desarrollo, expón el puerto con un túnel (por ejemplo `ngrok http 8000`) y registra esa URL pública como webhook en el panel de Meta for Developers.

---

## Deploy

El proyecto incluye un `Procfile` para Railway:

```
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Las variables de entorno se configuran directamente en el panel de Railway (el `.env` nunca se sube al repositorio).

---

## Estado del proyecto

Se usó de forma activa durante unos 2 meses para llevar mis gastos reales. Actualmente está detenido temporalmente, con estas limitaciones conocidas:

- Solo se procesan mensajes de **texto** (audios e imágenes se ignoran).
- El esquema de base de datos se crea con `create_all()`; no hay migraciones versionadas.
- La deduplicación de mensajes vive en memoria del proceso.
- Aún no hay suite de tests automatizados.

## Roadmap

- [ ] Validación de la firma `X-Hub-Signature-256` de Meta en el webhook
- [ ] Tests con pytest sobre `intent_router` y `date_utils`
- [ ] Migraciones con Alembic
- [ ] Procesamiento en background para responder a Meta de inmediato
- [ ] Edición y borrado de gastos ya registrados
- [ ] Presupuestos mensuales por categoría con alertas

---

## Licencia

MIT
