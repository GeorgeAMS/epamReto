# Reglas para Cursor / Agentes de IA — Pokédex Arcana Frontend

> **Lee este archivo ANTES de cualquier cambio.** Aplica a Cursor, Claude, Copilot, Windsurf y cualquier agente que toque este repo.

Este frontend tiene un **diseño aprobado** y un **stack específico**. Las reglas siguientes son **no negociables**.

---

## 0. Resumen del stack (no cambiar)

- **Framework**: TanStack Start v1 (React 19 + Vite 7) — **NO es Next.js**.
- **Routing**: TanStack Router file-based en `src/routes/`. NO React Router DOM, NO `src/pages/`.
- **Lenguaje**: TypeScript estricto.
- **Estilos**: Tailwind v4 vía `@import "tailwindcss"` en `src/styles.css`. NO `tailwind.config.js`.
- **Datos**: TanStack Query (`@tanstack/react-query`).
- **Animación**: Framer Motion.
- **Markdown**: `react-markdown` + `remark-gfm`.
- **Iconos**: `lucide-react`.

> Si Cursor sugiere migrar a Next.js, instalar otro router, o cambiar Tailwind a v3: **rechazar**.

---

## 1. Sistema de diseño — REGLAS DE ORO

El estilo es **"Pokémon oficial moderno"**: cartucho/Pokédex, paleta Pokéball, tipografías jugonas, bordes negros gruesos y sombras "duras".

### 1.1 Tokens — usar SIEMPRE las variables CSS de `src/styles.css`

```css
/* Paleta Pokémon (NO inventes otros nombres) */
--poke-red          /* primary */
--poke-red-dark
--poke-yellow       /* accent */
--poke-blue         /* secondary */
--poke-blue-dark
--poke-white
--poke-black        /* contornos y bordes SIEMPRE */
--poke-cream        /* fondo */

/* Tipos: --type-fire, --type-water, --type-electric, etc. */
```

### 1.2 Clases prohibidas en `className`

**NUNCA** uses estas clases hardcodeadas en componentes:

- `text-white`, `bg-white`, `bg-black`, `text-black`
- `bg-gray-*`, `bg-slate-*`, `bg-zinc-*`, `bg-neutral-*`
- `bg-purple-*`, `bg-indigo-*`, `bg-violet-*` (no es violeta, es ROJO Pokéball)
- `from-purple-*`, `via-purple-*`, `to-purple-*`
- `shadow-md`, `shadow-lg`, `shadow-xl` (usa la sombra "dura" Pokémon)

**USA en su lugar**:

```tsx
bg-poke-white       text-poke-black
bg-poke-red         text-poke-white
bg-poke-yellow      text-poke-black
bg-poke-blue        text-poke-white
bg-poke-cream
border-poke-black
shadow-[0_3px_0_0_var(--poke-black)]   // sombra dura "sticker"
shadow-[0_4px_0_0_var(--poke-black)]
shadow-[0_5px_0_0_var(--poke-black)]
```

### 1.3 Reglas visuales obligatorias

Cada componente nuevo debe seguir AL MENOS una de estas reglas:

1. **Bordes negros gruesos**: `border-2 border-poke-black` o `border-[3px] border-poke-black`. Nunca `border-gray-*`.
2. **Sombra dura tipo sticker**: `shadow-[0_Npx_0_0_var(--poke-black)]` (N entre 2 y 6). Nunca `shadow-md`/`shadow-lg`.
3. **Radius generoso**: `rounded-xl`, `rounded-2xl`, o `rounded-full` para chips/botones.
4. **Tipografía**:
   - Títulos: `font-display` (Fredoka).
   - Body: por defecto Nunito (no añadir clases).
   - Microtexto/labels/badges/contadores: `font-pixel text-[8px]` o `text-[9px]` (Press Start 2P) en MAYÚSCULAS.
5. **Botones primarios**: usa la receta Pokéball:
   ```tsx
   className="rounded-full bg-poke-red text-poke-white border-[3px] border-poke-black
              shadow-[0_3px_0_0_var(--poke-black)] font-bold
              hover:bg-poke-red-dark active:translate-y-0.5
              active:shadow-[0_1px_0_0_var(--poke-black)] transition-all"
   ```
6. **Cards / paneles**: usa `.poke-panel` o `.poke-panel-soft` (definidos en `styles.css`).

### 1.4 Tipos de Pokémon

Usa SIEMPRE `<TypeChip type="fire" />` (de `@/components/pokemon/TypeChip`). Nunca recrees colores de tipo a mano.

### 1.5 Pokéball

Para representar al asistente / branding, usa el SVG de Pokéball ya definido en:
- `src/components/layout/TopNav.tsx` (PokeballIcon)
- `src/routes/index.tsx` (ProfessorAvatar)

Si necesitas otra, **copia la misma estructura SVG**, no inventes otra.

---

## 2. Arquitectura — qué va dónde

```
src/
├── lib/api/              # ÚNICA capa de API. Todo fetch pasa aquí.
│   ├── client.ts
│   └── types.ts
├── features/             # Features con estado/lógica (chat, etc.)
├── components/
│   ├── layout/           # TopNav, footers, shells
│   ├── pokemon/          # Componentes Pokémon reutilizables
│   └── ui/               # shadcn primitives — NO editar a mano
├── routes/               # File-based routing TanStack
│   ├── __root.tsx        # Layout + QueryClientProvider + <head>
│   ├── index.tsx         # /
│   ├── explore.tsx       # /explore
│   ├── team.tsx          # /team
│   └── compare.tsx       # /compare
└── styles.css            # Tokens + utilities (FUENTE DE VERDAD del diseño)
```

### Reglas de arquitectura

- **NO crear `src/pages/`**, `app/layout.tsx`, ni rutas estilo Next.js.
- **NO editar `src/routeTree.gen.ts`** — se autogenera.
- **NO modificar `src/components/ui/*`** salvo orden explícita del usuario.
- Componentes Pokémon reutilizables van a `src/components/pokemon/`.
- Toda llamada al backend pasa por `src/lib/api/client.ts`. **PROHIBIDO** llamar `fetch` directamente desde componentes/páginas.

---

## 3. Backend e integración

- Variable única: `VITE_API_URL` (definida en `.env`). NO hardcodear URLs ni puertos en componentes.
- El cliente API ya soporta SSE y NDJSON en `/chat/stream`. No reescribir el parser sin razón.
- Endpoints soportados están en `README.md`. Si añades uno nuevo, añádelo al objeto `api` en `client.ts` y al README.

### Streaming — invariantes
- **Nunca truncar** mensajes largos. Si tocas `MessageBubble`, no añadas `line-clamp` al contenido del bot.
- **Nunca ocultar** datos de cálculo de daño (`DamageCard`). Es información crítica.
- Estados del pipeline (intent / agent) siempre visibles durante streaming.

---

## 4. Antipatrones — NO hagas esto

| ❌ Mal                                         | ✅ Bien                                                                  |
| ---------------------------------------------- | ------------------------------------------------------------------------ |
| `<button className="bg-blue-500 text-white">`  | `<button className="poke-btn bg-poke-blue text-poke-white px-4 py-1.5">` |
| `<div className="shadow-lg rounded-md">`       | `<div className="poke-panel-soft">` o sombra dura                        |
| `<a href="/explore">`                          | `<Link to="/explore">` (de `@tanstack/react-router`)                     |
| `fetch("http://127.0.0.1:18001/...")`          | `api.algo()` desde `@/lib/api/client`                                    |
| `import { useNavigate } from "react-router-dom"` | `import { useNavigate } from "@tanstack/react-router"`                 |
| Crear `tailwind.config.js`                     | Editar tokens en `src/styles.css`                                        |
| Modo oscuro / botón de tema                    | Mantener tema claro Pokédex (no implementar dark toggle)                 |
| Iconos emoji decorativos en cards principales  | Usar `lucide-react` o SVG Pokéball                                       |
| Gradientes morados (purple/violet/indigo)      | Gradientes rojo/amarillo/azul Pokémon                                    |
| Tipografía Inter / Poppins / Roboto sola       | `font-display` (Fredoka) + Nunito + `font-pixel` (Press Start 2P)        |

---

## 5. Checklist OBLIGATORIO antes de cada commit

- [ ] No usé `bg-white`, `text-white`, `bg-black`, `bg-gray-*`, `bg-purple-*` en `className`.
- [ ] Cualquier color nuevo lo añadí en `src/styles.css` como token, no inline.
- [ ] Botones tienen borde negro grueso + sombra dura.
- [ ] Cards usan `.poke-panel`, `.poke-panel-soft`, o equivalente con borde y sombra dura.
- [ ] Labels pequeños y badges usan `font-pixel` en MAYÚSCULAS.
- [ ] Títulos usan `font-display`.
- [ ] Llamadas al backend pasan por `lib/api/client.ts`.
- [ ] Navegación con `<Link>` de `@tanstack/react-router`, no `<a>`.
- [ ] No introduje `dark:` variants ni toggle de tema.
- [ ] No rompí `MessageBubble` (sin `line-clamp`/truncate en bot).
- [ ] No oculté ni reduje `DamageCard`.

---

## 6. Cuando dudes

1. Lee `src/styles.css` — es la **fuente de verdad** del sistema visual.
2. Mira un componente existente parecido (`PokemonCard`, `DamageCard`, `Composer`) y replica su estilo.
3. Si el estilo no encaja, **NO inventes**: pregunta al humano antes.

---

**Resumen ultra-corto para pegar al inicio de cada prompt en Cursor:**

> Stack: TanStack Start + Tailwind v4. Diseño Pokémon: paleta `--poke-red/yellow/blue/white/black/cream`, bordes `border-[3px] border-poke-black`, sombras duras `shadow-[0_Npx_0_0_var(--poke-black)]`, tipografías `font-display`/`font-pixel`. Prohibido `bg-white/black/gray/purple`, prohibido Next.js / React Router DOM, prohibido fetch directo (usar `lib/api/client`). Lee `AGENTS.md` antes de tocar nada.
