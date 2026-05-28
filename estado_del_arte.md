# Estado del Arte — Agentes de IA (Mayo 2026)

## 1. El campo en 2026

El modelo de "chat" es obsoleto para aplicaciones serias. En 2026, la arquitectura estándar es el **agente autónomo**: un LLM en un loop ReAct (Reason → Act → Observe) que decide qué herramientas usar, las ejecuta, procesa los resultados, y repite hasta completar la tarea.

Los diferenciadores reales ya no son los modelos (commoditized), sino:
- **Gestión de herramientas** a escala (50+ tools por agente)
- **Memoria semántica** persistente entre sesiones
- **Observabilidad**: trazas, métricas, replay de ejecuciones
- **Output estructurado** confiable (sin parsing frágil)

---

## 2. Frameworks principales (ranking 2026)

| Framework       | Paradigma            | Fortaleza principal                        | Usado por           |
|----------------|----------------------|--------------------------------------------|---------------------|
| **LangGraph**  | Graph-based workflow | Control fino, checkpointing, human-in-loop | Uber, LinkedIn, JPM |
| **PydanticAI** | Python-native agent  | Type safety, output estructurado, testable | Startups, fintechs  |
| **CrewAI**     | Multi-agent roles    | Multi-agente en < 50 líneas                | Prototipos rápidos  |
| **AutoGen/AG2**| Conversational agents| Debate entre agentes, Microsoft ecosystem  | Research, enterprises |
| **Smolagents** | Minimal agents       | Código Python como actions (HuggingFace)   | Research             |
| **Claude SDK** | Anthropic-native     | Mismo loop que Claude Code, integración API | Proyectos Anthropic  |

---

## 3. Por qué elegimos PydanticAI para este proyecto

### Criterios de selección

**Confiabilidad del output**: PydanticAI es el único framework que convierte la respuesta del LLM directamente en un objeto Pydantic validado. No hay parsing de JSON, no hay cadenas frágiles. El agente falla explícitamente si el modelo no respeta el schema.

**Python idiomático**: Tools son funciones Python con type hints. El schema de cada tool se genera automáticamente desde las anotaciones de tipo. Sin decoradores mágicos, sin YAML, sin DSLs.

**Agnóstico de proveedor**: Mismo código funciona con Claude, GPT-4, Gemini, DeepSeek, Llama (via Ollama). Cambiar de modelo = cambiar un string.

**Usage limits**: Configuración explícita de límites de tokens y llamadas a herramientas. Fundamental en producción.

### Lo que sacrificamos

- **Memoria semántica**: No incluida nativamente (a diferencia de CrewAI). Requiere implementación custom.
- **Multi-agente**: Sin handoffs entre agentes out-of-the-box. Se puede construir, pero no es primitivo.
- **Observabilidad**: Depende de integraciones externas (Langfuse, Logfire).

---

## 4. Stack elegido y justificación

```
Claude claude-sonnet-4-6     LLM de razonamiento + tool use nativo
PydanticAI 0.0.46+     Orquestación del agente, output estructurado
CoinGecko API (free)   Datos de mercado reales, sin auth
httpx                  HTTP moderno, async-compatible
Typer + Rich           CLI profesional con UI en terminal
python-dotenv          Configuración segura de secrets
```

### Por qué Claude claude-sonnet-4-6

- Tool use nativo y confiable (no propenso a alucinaciones de parámetros)
- Capacidad de razonamiento compleja para análisis de tendencias
- Velocidad/costo óptimo para loops de agente iterativos

### Por qué CoinGecko

- API pública sin API key para el tier básico
- Datos reales de precios, historial, market cap
- Perfecto para demos funcionales sin configuración

---

## 5. Arquitectura del agente Centinela

```
┌─────────────────────────────────────────────────────┐
│                    main.py (CLI)                    │
│           Typer commands → asyncio.run()            │
└──────────────────────┬──────────────────────────────┘
                       │  task (natural language)
                       ▼
┌─────────────────────────────────────────────────────┐
│              pricewatch/agent.py                    │
│    PydanticAI Agent  ←→  Claude claude-sonnet-4-6          │
│                                                     │
│    ReAct Loop:                                      │
│    1. Reason: qué herramienta usar                  │
│    2. Act:    llamar tool con parámetros             │
│    3. Observe: procesar resultado                   │
│    4. Repeat until → MarketReport (structured)      │
└──────────────────────┬──────────────────────────────┘
                       │  tool calls
          ┌────────────┼────────────┐
          ▼            ▼            ▼
   get_crypto_price  check_watchlist  save_alert
   get_price_history add_to_watchlist get_recent_alerts
   search_coin       remove_from_watchlist
          │            │            │
          └────────────┴────────────┘
                       │
          ┌────────────┴────────────┐
          ▼                         ▼
  CoinGecko REST API         data/*.json (local)
  (precios reales)           (watchlist + alerts)
```

### Flujo de ejecución típico (comando `scan`)

```
Agent recibe: "Full watchlist scan..."
  → tool: check_watchlist()
      resultado: [{bitcoin, low=$50k}, {ethereum, low=$2k}]
  → tool: get_crypto_price("bitcoin")
      resultado: {price: $67,420, change_24h: +2.1%}
  → tool: get_price_history("bitcoin", days=7)
      resultado: {trend: "bullish", change_pct: +8.3%}
  → tool: get_crypto_price("ethereum")
      resultado: {price: $3,180, change_24h: -0.8%}
  → tool: get_price_history("ethereum", days=7)
      resultado: {trend: "sideways", change_pct: +1.2%}
  → [decide: ningún breach de threshold]
  → RETURN MarketReport(
        summary="BTC en $67,420 (+8.3% semana)...",
        alerts=[],
        recommendations=["BTC acercándose a resistencia $70k..."],
        coins_analyzed=["bitcoin", "ethereum"]
    )
```

---

## 6. Tendencias clave 2026

**MCP (Model Context Protocol)**: Standard de Anthropic para conectar LLMs con fuentes de datos externas. Reemplaza gradualmente los wrappers custom.

**Computer use + vision**: Agentes que ven la pantalla y actúan como usuarios (ya en producción con Claude).

**Agentic pipelines en CI/CD**: Code review, testing, deployment automatizados por agentes.

**Memory as a service**: Backends semánticos (Mem0, Zep) que dan a los agentes persistencia entre conversaciones.

**Output estructurado obligatorio**: El campo migró de "best effort JSON parsing" a validación estricta con Pydantic/Zod como estándar.

---

*Investigación realizada: Mayo 2026. Fuentes: Alice Labs AI Rankings, Speakeasy Framework Comparison, Langfuse Open-Source Comparison, PydanticAI docs.*
