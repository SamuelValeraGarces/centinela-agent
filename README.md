# Centinela - AI Market Monitor Agent

Agente autonomo que monitorea precios de criptomonedas en tiempo real, analiza tendencias y te envia alertas directamente a WhatsApp.

Construido con **PydanticAI** (framework de agentes IA, 2026) + **Claude Sonnet** + **CoinGecko API** + **Twilio WhatsApp**.

---

## Como funciona

El agente corre un loop ReAct (Razonar -> Actuar -> Observar) donde Claude decide que herramientas usar en cada paso:

```
Tu comando (lenguaje natural)
        |
        v
  Claude Sonnet (razona)
        |
        v
  Llama tools: get_crypto_price / get_price_history / check_watchlist / save_alert / ...
        |
        v
  Analiza resultados, decide proxima accion
        |
        v
  Devuelve MarketReport (estructura Pydantic validada)
        |
        v
  Muestra en terminal + envia a tu WhatsApp
```

---

## Requisitos

- Python 3.10+
- Cuenta en [Anthropic Console](https://console.anthropic.com) (para la API key)
- Cuenta en [Twilio](https://twilio.com) (gratis, solo para WhatsApp)

---

## Instalacion

```bash
git clone https://github.com/SamuelValeraGarces/centinela-agent
cd centinela-agent
pip install -r requirements.txt
```

---

## Configuracion

Copia el archivo de ejemplo y completa tus credenciales:

```bash
cp .env.example .env
```

Edita `.env`:

```env
# API key de Anthropic -> https://console.anthropic.com
ANTHROPIC_API_KEY=sk-ant-...

# Credenciales de Twilio -> https://console.twilio.com
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Numero del sandbox de Twilio (este es el fijo del sandbox gratuito)
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886

# Tu numero de WhatsApp personal (con codigo de pais)
WHATSAPP_TO=whatsapp:+549XXXXXXXXXX
```

### Activar el sandbox de WhatsApp (Twilio)

1. Entra a [console.twilio.com](https://console.twilio.com) -> Messaging -> Try it out -> Send a WhatsApp message
2. Desde tu WhatsApp, manda el mensaje que te indica (algo como `join <palabra>`) al numero de Twilio
3. Recibes confirmacion -> ya podes recibir mensajes del agente

---

## Uso

### Scan autonomo (comando principal)

Chequea todas las monedas del watchlist, detecta breaches de umbrales y envia reporte a WhatsApp:

```bash
python main.py scan
```

### Agregar moneda al watchlist

```bash
# Solo seguimiento, sin alertas
python main.py watch bitcoin

# Con alerta de precio bajo
python main.py watch ethereum --low 2000

# Con alerta de precio alto
python main.py watch bitcoin --high 90000

# Con ambas alertas
python main.py watch solana --low 100 --high 200
```

### Consultar precios rapidos

```bash
python main.py prices bitcoin ethereum solana
```

### Tarea en lenguaje natural

```bash
python main.py run "Analiza el mercado cripto esta semana y decime si es buen momento para entrar en ethereum"

python main.py run "Agrega bitcoin con alerta si baja de 60000 o sube de 90000, y dame el precio actual"
```

### Ver watchlist y alertas guardadas

```bash
python main.py watchlist
python main.py alerts
python main.py alerts --limit 30
```

---

## Ejemplo de salida

```
+---------------------------------------------------------------+
| Centinela - AI Market Monitor Agent                           |
| Task: Full watchlist scan...                                  |
+---------------------------------------------------------------+

Agent thinking...

+----------------------- Market Report -------------------------+
|                                                               |
|  Bitcoin cotiza a $74,233 (+2.1% en 24h). Tendencia semanal  |
|  bullish con +8.3% en 7 dias. Ethereum en $3,180, sideways.  |
|  Ningun umbral alcanzado en este scan.                        |
|                                                               |
+---------------------------------------------------------------+

Recommendations
  - BTC acercandose a resistencia $75k, considerar take-profit parcial
  - ETH muestra consolidacion, posible entrada en soporte $3,000

Analyzed: BITCOIN  ETHEREUM

Tokens: 1842 in / 312 out | Tool calls: 6 | Total: 2154
WhatsApp sent (SID: SMxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx)
```

Y en tu WhatsApp llega:

```
*[ Centinela -- Market Report ]*

Bitcoin cotiza a $74,233 (+2.1% en 24h). Tendencia semanal
bullish con +8.3% en 7 dias...

*-- Recomendaciones --*
  - BTC acercandose a resistencia $75k
  - ETH muestra consolidacion en soporte $3,000

Analizadas: BITCOIN, ETHEREUM
```

---

## Stack tecnico

| Componente | Tecnologia | Por que |
|---|---|---|
| Framework agente | PydanticAI 1.x | Output estructurado validado por Pydantic, Python idiomatico |
| LLM | Claude Sonnet (Anthropic) | Tool use confiable, razonamiento analitico |
| Datos de mercado | CoinGecko API | Gratis, sin auth, precios reales |
| Notificaciones | Twilio WhatsApp | API oficial, sandbox gratuito para testing |
| CLI | Typer + Rich | Interface profesional en terminal |
| Persistencia | JSON local | Simple, sin dependencias de DB |

### Herramientas del agente (tools)

El agente tiene 9 herramientas que llama autonomamente segun la tarea:

| Tool | Descripcion |
|---|---|
| `get_crypto_price` | Precio actual + cambio 24h via CoinGecko |
| `get_price_history` | Historial de precios + clasificacion de tendencia (1-30 dias) |
| `search_coin` | Busca el ID correcto de una moneda en CoinGecko |
| `check_watchlist` | Lee el watchlist actual |
| `add_to_watchlist` | Agrega/actualiza moneda con umbrales de alerta |
| `remove_from_watchlist` | Elimina moneda del watchlist |
| `save_alert` | Persiste una alerta en el log local |
| `get_recent_alerts` | Lee alertas recientes del log |
| `send_whatsapp_alert` | Envia alerta inmediata por WhatsApp via Twilio |

---

## Estructura del proyecto

```
centinela-agent/
├── main.py                  # CLI (Typer) - entry point
├── pricewatch/
│   ├── agent.py             # Agente PydanticAI + registro de tools
│   ├── models.py            # Modelos Pydantic (MarketReport, WatchEntry, etc.)
│   ├── tools.py             # Funciones I/O: CoinGecko API + storage
│   ├── notifier.py          # Notificaciones WhatsApp via Twilio
│   └── storage.py           # Lectura/escritura JSON
├── data/                    # Creado automaticamente en el primer uso
│   ├── watchlist.json       # Monedas monitoreadas (git-ignored)
│   └── alerts.json          # Log de alertas (git-ignored)
├── estado_del_arte.md       # Investigacion de frameworks de agentes IA 2026
├── requirements.txt
└── .env.example
```
