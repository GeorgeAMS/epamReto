# Prompt inicial sugerido para Cursor

Pega esto en tu primer mensaje a Cursor (Chat o Composer):

---

Estoy trabajando en **Pokédex Arcana**, frontend en **TanStack Start (React 19 + Vite 7 + TS estricto)** con **Tailwind v4** y diseño visual estilo **Pokémon oficial** (paleta Pokéball: rojo/amarillo/azul/blanco/negro/cream, bordes negros gruesos, sombras "duras" tipo sticker, tipografías Fredoka + Nunito + Press Start 2P).

**Antes de cualquier cambio**, lee y respeta:
1. `AGENTS.md` (reglas completas de diseño y arquitectura)
2. `.cursorrules` (resumen estricto)
3. `src/styles.css` (tokens — fuente de verdad visual)

**Reglas no negociables**:
- NO migrar a Next.js, NO React Router DOM, NO Tailwind v3.
- NO usar `bg-white/black/gray/purple/violet/indigo` ni `shadow-md/lg/xl`.
- SIEMPRE bordes `border-[3px] border-poke-black` + sombra `shadow-[0_Npx_0_0_var(--poke-black)]`.
- Toda llamada al backend pasa por `src/lib/api/client.ts` (nunca `fetch` directo).
- URL backend solo via `VITE_API_URL`.
- Nunca truncar mensajes del bot ni ocultar `DamageCard`.

Si algo no encaja con el diseño Pokémon o no estás seguro, **pregunta antes de inventar**.
