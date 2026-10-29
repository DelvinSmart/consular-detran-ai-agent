# Consular & DETRAN AI Agent

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-API-009688?logo=fastapi&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o--mini-412991?logo=openai&logoColor=white)
![Gemini](https://img.shields.io/badge/Google-Gemini-4285F4?logo=googlegemini&logoColor=white)
![WhatsApp](https://img.shields.io/badge/WhatsApp-Cloud%20API-25D366?logo=whatsapp&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green.svg)

Agente de IA con arquitectura **RAG** (Retrieval-Augmented Generation) que
orienta a personas migrantes sobre **trámites de DETRAN, licencias de
conducir y cartas consulares**, respondiendo **solo** con lo que dicen los
documentos de referencia que se le entregan.

Está construido como un **agente headless**: el núcleo de inteligencia no
sabe nada de HTTP, HTML ni WhatsApp. Cada canal es un adaptador delgado que
traduce mensajes hacia y desde el mismo cerebro.

## El problema

La información sobre cómo canjear una licencia extranjera o conseguir una
carta consular está repartida en PDFs, portales estatales y sitios de
consulados, muchas veces en otro idioma. Un chatbot genérico "rellena los
huecos" con plazos, costos o requisitos inventados, y en un trámite
migratorio un dato inventado puede costar una cita perdida o una multa.

Este proyecto prioriza que **el agente diga "no lo sé" antes que inventar**.

## Arquitectura

```
                    ┌──────────────────────────────────────────┐
                    │          agent_core  (el cerebro)        │
                    │                                          │
  data/documents ──▶│  ingestion ─▶ embeddings ─▶ vector_store │
   (PDF/TXT/MD)     │                                  │       │
                    │  pregunta ─▶ embed ─▶ búsqueda ◀─┘       │
                    │                 │                        │
                    │      ¿similitud ≥ umbral? ── no ─▶ "no sé"│
                    │                 │ sí                     │
                    │      LLM (contexto estricto, temp 0)     │
                    │                 │                        │
                    │            Answer + fuentes              │
                    └───────────────┬──────────────────────────┘
                                    │  RAGAgent.ask(texto) -> Answer
              ┌─────────────────────┼──────────────────────┐
              ▼                     ▼                      ▼
     channels/web.py       channels/whatsapp.py      scripts/ask.py
     POST /api/chat        /webhooks/whatsapp         (terminal)
              │                     │
       web/ (panel chat)    Meta WhatsApp Cloud API
```

| Capa | Carpeta | Responsabilidad |
| --- | --- | --- |
| Núcleo | [`agent_core/`](agent_core/) | Ingesta, embeddings, índice, recuperación y generación. Sin dependencias de canal. |
| Proveedores | [`agent_core/providers/`](agent_core/providers/) | OpenAI y Gemini detrás de una misma interfaz (`embed` + `generate`). Agregar otro = una clase. |
| Canales | [`channels/`](channels/) | Adaptadores: API web y webhook de WhatsApp. Solo traducen formatos. |
| Interfaz | [`web/`](web/) | Panel de chat estático para pruebas visuales. |
| Servidor | [`server.py`](server.py) | Ensambla los canales en una app FastAPI. Sin lógica de IA. |

### Barreras anti-alucinación

1. **Umbral de similitud** (`MIN_SIMILARITY`): si ningún fragmento recuperado
   es suficientemente parecido a la pregunta, el agente declina **sin llamar
   al modelo**.
2. **Prompt de contexto estricto** ([`prompts.py`](agent_core/prompts.py)):
   el modelo solo puede usar el contexto, debe citar `[n]` y tiene una frase
   exacta para cuando no sabe; además ignora instrucciones incrustadas en
   los documentos (prompt injection).
3. **Temperatura 0** y detección de la frase de rechazo: la respuesta se
   marca `grounded: false` y no muestra fuentes.
4. **Índice atado a su modelo de embeddings**: si cambias de proveedor sin
   reindexar, el agente se niega a arrancar en vez de devolver resultados
   sin sentido.

### Contrato de respuesta

Todos los canales reciben el mismo objeto:

```json
{
  "answer": "Para el canje necesitas... [1]",
  "grounded": true,
  "sources": [
    { "source": "guia_detran_am.pdf", "page": 3, "score": 0.82, "excerpt": "..." }
  ]
}
```

## Instalación local

Requisitos: Python 3.10+ y una API key de OpenAI **o** de Gemini.

```bash
git clone https://github.com/DelvinSmart/consular-detran-ai-agent.git
cd consular-detran-ai-agent

python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env             # y completa OPENAI_API_KEY o GEMINI_API_KEY
```

### 1. Cargar documentos e indexar

Pon tus PDFs/TXT/MD oficiales en [`data/documents/`](data/documents/). El
repo trae `ejemplo_guia_demo.md`, un documento **ficticio** solo para probar
el flujo.

```bash
python scripts/ingest.py
# Indexando data/documents con openai/text-embedding-3-small...
# Listo: 2 fragmentos guardados en data/index/index.json
```

Vuelve a ejecutarlo cada vez que agregues o cambies documentos, o cambies de
proveedor.

### 2. Probar

Desde la terminal:

```bash
python scripts/ask.py "¿Para qué sirve una carta consular?"
```

Panel web + API:

```bash
uvicorn server:app --reload
```

- Panel de chat: <http://localhost:8000>
- Documentación interactiva de la API: <http://localhost:8000/docs>

### 3. Tests

Los tests usan un proveedor falso: no necesitan API key ni internet.

```bash
pytest
```

## Conectar WhatsApp Business (opcional)

El adaptador [`channels/whatsapp.py`](channels/whatsapp.py) ya implementa la
verificación del webhook, la validación de firma `X-Hub-Signature-256`, la
extracción de mensajes de texto y el envío de la respuesta por la Cloud API
de Meta. Viene **desactivado** (`WHATSAPP_ENABLED=false`, las rutas
responden 404).

1. Crea una app en [Meta for Developers](https://developers.facebook.com/)
   con el producto **WhatsApp**.
2. Completa en `.env`: `WHATSAPP_VERIFY_TOKEN` (lo inventas tú),
   `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`,
   `WHATSAPP_APP_SECRET` y `WHATSAPP_ENABLED=true`.
3. Expón el servidor con HTTPS, por ejemplo `ngrok http 8000`.
4. En la configuración del webhook de Meta registra
   `https://<tu-dominio>/webhooks/whatsapp` con el mismo verify token y
   suscríbete al campo `messages`.

El mismo `RAGAgent` que responde en el panel web responde en WhatsApp: no
hay que duplicar documentos, prompts ni lógica.

## Seguridad

- Ningún secreto vive en el código: todo sale de `.env`, que está en
  `.gitignore` junto con cualquier `.env.*` (salvo `.env.example`).
- Los documentos reales y el índice generado **no se commitean**: pueden
  contener datos personales o material con derechos de autor.
- El panel web pinta las respuestas con `textContent`, nunca como HTML.
- El webhook rechaza peticiones sin firma HMAC válida de Meta.

## Estructura

```
consular-detran-ai-agent/
├── agent_core/            # Núcleo headless (cerebro RAG)
│   ├── config.py          # Settings desde variables de entorno
│   ├── models.py          # Chunk, Source, Answer (Pydantic)
│   ├── ingestion.py       # Lectura PDF/TXT/MD + chunking con solapamiento
│   ├── vector_store.py    # Índice JSON + similitud coseno
│   ├── prompts.py         # Prompt de contexto estricto
│   ├── engine.py          # RAGAgent.ask() y build_index()
│   └── providers/         # OpenAI / Gemini intercambiables
├── channels/              # Adaptadores de canal
│   ├── web.py             # POST /api/chat
│   └── whatsapp.py        # Webhook WhatsApp Cloud API (desactivado)
├── web/                   # Panel de chat de pruebas
├── scripts/               # ingest.py, ask.py
├── data/documents/        # Documentos de referencia
├── tests/                 # Tests sin API key
└── server.py              # App FastAPI
```

## Próximos pasos

- Base vectorial persistente (pgvector / Qdrant) para corpus grandes.
- Memoria de conversación por usuario (historial corto por número de WhatsApp).
- Metadatos por estado (DETRAN-AM, DETRAN-SP...) para filtrar la recuperación.
- Evaluación automática de respuestas con un set de preguntas de referencia.

## Aviso

Este agente ofrece **orientación informativa** basada en los documentos
cargados. No reemplaza la información oficial del DETRAN ni de los
consulados.

## Licencia

[MIT](LICENSE)
