# Pokédex Arcana — Frontend

Frontend premium para el backend FastAPI **Pokédex Arcana**. Stack: TanStack Start (React 19 + Vite 7), TypeScript estricto, Tailwind v4, TanStack Query, Framer Motion.

## Setup

```bash
bun install
cp .env.example .env   # ajusta VITE_API_URL
bun dev
```

## Variables de entorno

| Variable        | Descripción                                                        | Default                  |
| --------------- | ------------------------------------------------------------------ | ------------------------ |
| `VITE_API_URL`  | URL base del backend FastAPI. Cambia aquí, no en componentes.      | `http://127.0.0.1:18001` |

Para producción/preview público, apunta a tu URL de Railway/Render/ngrok:
```
VITE_API_URL=https://api.tudominio.com
```

## Arquitectura

```
src/
├── lib/api/              # Capa única de API
│   ├── client.ts         #   fetch wrapper + streamChat (SSE/NDJSON)
│   └── types.ts          #   Tipos TS de todas las respuestas
├── features/
│   ├── chat/             #   useChat, MessageBubble, Composer, PipelineIndicator
│   └── explore/          #   (extensible)
├── components/
│   ├── layout/TopNav.tsx
│   ├── pokemon/          #   PokemonCard, PokemonModal, TypeChip,
│   │                     #   ConfidenceBadge, SourcesPopover, DamageCard
│   └── ui/               #   shadcn primitives
├── routes/               #   File-based routing (TanStack Router)
│   ├── __root.tsx        #   Layout + QueryClientProvider + <head>
│   ├── index.tsx         #   /        Chat
│   ├── explore.tsx       #   /explore Pokédex grid
│   ├── team.tsx          #   /team    (placeholder v2)
│   └── compare.tsx       #   /compare — stats 2–4 Pokémon
└── styles.css            # Design tokens + utilities
```

### Endpoints soportados

| Método | Endpoint                 | Cliente                          |
| ------ | ------------------------ | -------------------------------- |
| GET    | `/health`                | `api.health()`                   |
| POST   | `/chat`                  | `api.chat()`                     |
| POST   | `/chat/stream`           | `streamChat()` (SSE/NDJSON)      |
| GET    | `/conversations`         | `api.conversations()`            |
| DEL    | `/conversations/{id}`    | `api.deleteConversation()`       |
| GET    | `/traces/{id}`           | `api.traces()`                   |
| POST   | `/compare/`              | `api.comparePokemon([...])`      |
| GET    | `/pokedex/pokemon`       | `api.pokedexList(filters)`       |
| GET    | `/pokedex/types`         | `api.pokedexTypes()`             |
| GET    | `/pokedex/generations`   | `api.pokedexGenerations()`       |

### Streaming

`streamChat()` parsea **SSE estándar** (`data: {...}\n\n`) y **NDJSON** indistintamente. Eventos esperados (todos opcionales):

```ts
{ type: "intent",     intent: "damage_calc" }
{ type: "agent",      agent:  "calc_engine" }
{ type: "token",      token:  "Garchomp" }      // o delta/text/content
{ type: "sources",    sources: [{ title, url, snippet }] }
{ type: "confidence", confidence: "verified" | "partial" | "contradiction" }
{ type: "damage",     damage: { attacker, defender, move, damage_range, percent_range, type_effectiveness, ... } }
{ type: "done" }
{ type: "error",      message: "…" }
```

Si tu backend emite tokens como string plano por línea, también funciona.

## Comandos

```bash
bun dev        # dev server
bun run build  # build prod (lo corre la plataforma)
```

## QA Checklist (manual)

Probar contra el backend con estos prompts:

- [ ] **Stats**: "Dame stats base de Garchomp" → respuesta markdown + fuentes + badge de confianza, sin truncar.
- [ ] **Lore**: "Cuéntame el lore de Pikachu en Kanto" → respuesta narrativa con fuentes.
- [ ] **Strategy**: "Recomienda equipo para Garchomp en OU" → equipo + coberturas en markdown.
- [ ] **Damage calc**: "¿Cuánto daño hace Garchomp con Earthquake contra Blissey defensiva estándar?" → **DamageCard** visible con rango, %, type effectiveness y barra al HP.
- [ ] **Damage + weather**: "Rain-boosted Hydro from Venusaur to Charizard — recheck numbers?" → DamageCard con weather=Rain.
- [ ] **Streaming**: tokens aparecen progresivamente; pipeline muestra intent y agent.
- [ ] **Stop**: botón cuadrado detiene la generación; el contenido parcial se mantiene.
- [ ] **Retry**: tras error de red, banner rojo con botón Reintentar reenvía el último mensaje.
- [ ] **Sources**: popover lista títulos y abre links en nueva pestaña.
- [ ] **No truncado**: respuestas largas mantienen scroll, sin recortar contenido.
- [ ] **Explore**: filtros por type/gen y búsqueda funcionan; modal muestra stats con barras.
- [ ] **Mobile**: navegación, composer y grid usables a 375px.
