# Finance Bot — WhatsApp Personal Finance Tracker

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?logo=postgresql&logoColor=white)
![Groq](https://img.shields.io/badge/Groq-llama--3.3--70b-F55036)
![pytest](https://img.shields.io/badge/tests-pytest-0A9EDC?logo=pytest&logoColor=white)

Bot de WhatsApp para registrar y consultar gastos personales mediante lenguaje natural. Proyecto de portafolio construido con Python y FastAPI.

> **"Gasté 350 en uber al trabajo"** → el bot extrae el monto, la categoría y la descripción, y los guarda automáticamente en la base de datos.

---

## Demo

> _(Pendiente: capturas o GIF de una conversación real con el bot.)_

---

## ¿Qué hace?

El usuario le escribe al bot por WhatsApp en texto libre — sin formularios, sin comandos. El bot entiende el mensaje, extrae los datos, los persiste en PostgreSQL y confirma al usuario con un mensaje de vuelta. Los usuarios se crean solos la primera vez que escriben, identificados por su número de WhatsApp.

| Funcionalidad | Ejemplo de mensaje | Respuesta |
|---|---|---|
| **Registro de gastos** | `Gasté 350 en uber al trabajo` | ✅ Gasto registrado: *RD$350.00* en pasaje (uber al trabajo) |
| **Varios gastos a la vez** | `Gasté 200 en almuerzo y 150 en el pasaje` | Un registro y una confirmación por cada gasto |
| **Consultas por período** | `¿Cuánto gasté en comida este mes?` | Gastaste *RD$4,250.00* en comida este mes |
| **Total general** | `¿Cuánto gasté la semana pasada?` | Tu gasto total la semana pasada: *RD$…* |
| **Resumen por categorías** | `¿En qué gasté este mes?` | Total de cada categoría + total general |
| **Desglose de una categoría** | `Desglósame mis gastos de salud` | Lista línea por línea con fecha, monto y descripción + total |
| **Atajo por categoría** | `comida` | Total del mes en esa categoría |
| **Búsqueda por descripción** | `uber` | Gastaste *RD$1,200.00* en: "uber" este mes |
| **Gastos fijos** | `Netflix los 12 de cada mes por 400` | 📍 Pago fijo registrado: *RD$400.00* - Netflix (servicios)… Próximo: 12/10/2026 (faltan 21 días) |
| **Consulta de pagos fijos** | `¿Cuándo pago el préstamo del BHD?` | Próxima fecha de cobro y días restantes |
| **Lista de pagos fijos** | `¿Cuáles son mis pagos fijos?` | Todos los pagos activos, ordenados por cercanía, con el total mensual |
| **Mensajes combinados** | `Hola, gasté 200 en comida. ¿Cuánto llevo gastado?` | Saluda, registra el gasto y responde la pregunta |

**Períodos soportados:** hoy, ayer, esta semana, semana pasada, este mes (por defecto), mes pasado y días puntuales del mes actual (`¿cuánto gasté el 15?`).

**Atajo por categoría:** el mensaje tiene que ser exactamente el nombre de la categoría (`comida`, `salud`, `cuidado_personal`…). Si el mensaje no encaja en ninguna intención, el bot busca ese texto dentro de las descripciones de los gastos del mes; si tampoco hay coincidencias, responde con un mensaje de ayuda.

---

## Stack

| Capa | Tecnología |
|---|---|
| API | Python + FastAPI |
| LLM | Groq (`llama-3.3-70b-versatile`) en modo JSON |
| Validación | Pydantic v2 + pydantic-settings |
| ORM | SQLAlchemy 2.x |
| Base de datos | PostgreSQL en Neon |
| Mensajería | Meta WhatsApp Business API (Graph API v25.0) |
| Tests | pytest |
| Deploy | Railway |

---

## Arquitectura

```
app/
├── core/           # Configuración (pydantic-settings) y conexión a base de datos
├── models/         # Modelos SQLAlchemy (Usuario, Gasto, GastoFijo) y el enum CategoriaGasto
├── schemas/        # Modelos Pydantic que validan lo que devuelve el LLM
├── repositories/   # Queries a la base de datos (gastos, gastos fijos, usuarios)
├── services/       # Lógica de negocio (orquestación, intent router, consultas, gastos fijos, fechas)
├── integrations/   # Clientes externos (Groq, WhatsApp)
├── routers/        # Endpoint del webhook
└── main.py         # App FastAPI, creación de tablas y endpoints de estado
tests/              # Tests con pytest
```

**Principio de diseño clave:** el LLM actúa como capa de interpretación delgada — extrae intención estructurada del texto libre, pero **nunca genera ni ejecuta SQL**. Python construye todas las queries y Pydantic valida cada respuesta del modelo antes de usarla. Esto mantiene el sistema predecible y auditable.

**Flujo completo:**

```
WhatsApp → Meta API → webhook.py → expense_service.procesar_mensaje
                                         │
                                         ├─ intent_router (reglas léxicas, sin LLM)
                                         ├─ groq_client (extrae los datos del texto)
                                         ├─ query_service / gasto_fijo_service
                                         └─ repositories → PostgreSQL (Neon)
                                         │
                                         ▼
                                   whatsapp_client → WhatsApp (respuesta)
```

### Intent Router
Reglas léxicas simples (sin ML) para clasificar cada mensaje: registro de gasto, registro de gasto fijo, pregunta sobre gastos, pregunta sobre pagos fijos o saludo. Devuelve una **lista** de intenciones, así un solo mensaje puede disparar varias acciones. La decisión es barata (microsegundos, sin costo de API) y reserva el LLM para lo que sí justifica su uso: extraer monto, categoría, descripción, período o día de cobro del texto libre.

### Webhook
Además de recibir los mensajes de Meta, el webhook:
- deduplica mensajes ya procesados (Meta reintenta entregas),
- envía el indicador de "escribiendo…" y marca el mensaje como leído mientras procesa,
- ignora sin error los eventos que no son mensajes de texto (estados de entrega, audios, imágenes), para que Meta no lo dé por caído.

### Fechas y zona horaria
Los gastos se guardan en UTC. Las consultas calculan los rangos (hoy, esta semana, este mes…) en hora de República Dominicana (UTC-4, sin horario de verano) y los convierten a UTC antes de consultar la base.

### Gastos fijos
Se guardan como plantilla (`descripcion`, `monto`, `dia_mes`) y la próxima fecha de cobro se calcula en tiempo real. Si un pago cae el 31 y el mes tiene 30 días, el cobro se ajusta al último día del mes. La capa de datos ya permite desactivar un pago fijo (se marca como inactivo en lugar de borrarlo, para no perder el historial), pero todavía no hay un mensaje de WhatsApp que lo dispare.

### Categorías de gasto
Enum cerrado definido en `app/models/categorias.py`, sin dependencias de la base de datos: `comida`, `pasaje`, `cuidado_personal`, `servicios`, `salud`, `salidas`, `ahorros`, `pedidos`, `pagos`, `otros`.

---

## Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/` | Identifica el servicio y apunta a la documentación |
| `GET` | `/health` | Healthcheck real: hace `SELECT 1` contra Postgres y devuelve `503` si la base no responde |
| `GET` | `/webhook` | Verificación del webhook que hace Meta al configurarlo |
| `POST` | `/webhook` | Recibe los mensajes entrantes de WhatsApp |

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

pip install -r requirements-dev.txt   # o requirements.txt si no vas a correr tests
cp .env.example .env         # y completa los valores

uvicorn app.main:app --reload
```

La API queda en `http://localhost:8000` y la documentación interactiva en `http://localhost:8000/docs`. Las tablas se crean solas al arrancar.

Para que Meta pueda llegar a tu máquina durante el desarrollo, expón el puerto con un túnel (por ejemplo `ngrok http 8000`) y registra esa URL pública más `/webhook` en el panel de Meta for Developers.

---

## Tests

Las dependencias de desarrollo están en `requirements-dev.txt`, que incluye las de producción más `pytest`. Los tests viven en `tests/` y `pytest.ini` ya configura el `pythonpath`, así que basta con correr desde la raíz del proyecto:

```bash
pip install -r requirements-dev.txt
pytest
```

Hoy cubren `date_utils` (cálculo de la próxima fecha de cobro de un gasto fijo): mismo mes, cambio de mes, cambio de año, meses cortos y años bisiestos. Las funciones reciben la fecha de "hoy" como parámetro, así los tests no dependen del reloj y dan el mismo resultado cualquier día. No necesitan base de datos ni variables de entorno.

---

## Deploy

El proyecto incluye un `Procfile` para Railway:

```
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Las variables de entorno se configuran directamente en el panel de Railway (el `.env` nunca se sube al repositorio). El endpoint `/health` sirve como healthcheck del servicio.

---

## Estado del proyecto

Se usó de forma activa durante unos 2 meses para llevar mis gastos reales. Actualmente está detenido temporalmente, con estas limitaciones conocidas:

- Solo se procesan mensajes de **texto** (audios e imágenes se ignoran).
- El esquema de base de datos se crea con `create_all()`; no hay migraciones versionadas.
- La deduplicación de mensajes vive en memoria del proceso (se pierde al reiniciar y no se comparte entre instancias).
- El mensaje se procesa dentro del request del webhook, así que Meta espera a que terminen las llamadas a Groq y a la base antes de recibir su respuesta.
- La zona horaria está fija en UTC-4.
- Los tests solo cubren `date_utils` por ahora.

## Roadmap

- [x] Tests con pytest sobre `date_utils`
- [ ] Tests con pytest sobre `intent_router`
- [ ] Validación de la firma `X-Hub-Signature-256` de Meta en el webhook
- [ ] Migraciones con Alembic
- [ ] Procesamiento en background para responder a Meta de inmediato
- [ ] Cancelar un pago fijo desde WhatsApp
- [ ] Edición y borrado de gastos ya registrados
- [ ] Presupuestos mensuales por categoría con alertas

---

## Licencia

[MIT](LICENSE)
