import type { Pokemon } from "@/lib/api/types";
import { TypeChip } from "./TypeChip";
import { motion } from "framer-motion";

const fallback = (id: number) => `https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/${id}.png`;

export function PokemonCard({ pokemon, onClick }: { pokemon: Pokemon; onClick?: (p: Pokemon) => void }) {
  const img = pokemon.artwork ?? pokemon.sprite ?? (pokemon.id ? fallback(pokemon.id) : undefined);
  const primary = pokemon.types?.[0] ?? "normal";
  return (
    <motion.button
      layout
      whileHover={{ y: -5, rotate: -1 }}
      whileTap={{ scale: 0.97 }}
      onClick={() => onClick?.(pokemon)}
      className="group relative flex flex-col overflow-hidden rounded-2xl border-[3px] border-poke-black bg-poke-white p-3 text-left shadow-[0_4px_0_0_var(--poke-black)] hover:shadow-[0_6px_0_0_var(--poke-black)] transition-shadow"
    >
      {/* Banda de color por tipo */}
      <div className={`pointer-events-none absolute inset-x-0 top-0 h-16 type-${primary} opacity-90`} />
      <div className="pointer-events-none absolute inset-x-0 top-16 h-[3px] bg-poke-black" />
      {/* Pokéball decorativa */}
      <svg viewBox="0 0 64 64" className="pointer-events-none absolute -right-4 -top-4 h-20 w-20 opacity-25" aria-hidden="true">
        <circle cx="32" cy="32" r="29" fill="#fff" stroke="#1a1a1a" strokeWidth="3" />
        <path d="M3 32 a29 29 0 0 1 58 0 z" fill="rgba(0,0,0,0)" stroke="#1a1a1a" strokeWidth="3" />
        <line x1="3" y1="32" x2="61" y2="32" stroke="#1a1a1a" strokeWidth="3" />
        <circle cx="32" cy="32" r="8" fill="#fff" stroke="#1a1a1a" strokeWidth="3" />
      </svg>

      <div className="relative z-[1] flex min-h-0 flex-1 flex-col">
        <div className="shrink-0 font-pixel text-[9px] text-poke-white drop-shadow-[1px_1px_0_rgba(0,0,0,0.6)]">
          N°{String(pokemon.id ?? 0).padStart(3, "0")}
        </div>
        {/* Área del arte: recorte estricto para que el hover no tape el nombre */}
        <div className="relative z-[1] mx-auto mt-1 flex h-[7.25rem] w-full max-w-[9.5rem] shrink-0 items-end justify-center overflow-hidden">
          {img ? (
            <img
              src={img}
              alt={pokemon.name}
              loading="lazy"
              className="max-h-full max-w-full object-contain object-bottom transition-transform duration-200 group-hover:scale-[1.04]"
            />
          ) : (
            <div className="h-24 w-24 shrink-0 rounded-xl skeleton" />
          )}
        </div>
        {/* Bloque de texto siempre encima del arte residual */}
        <div className="relative z-20 mt-2 shrink-0 rounded-lg bg-poke-white px-0.5 pt-1 text-center">
          <div className="font-display font-bold capitalize text-base leading-snug text-poke-black">{pokemon.name}</div>
          <div className="mt-1.5 flex flex-wrap justify-center gap-1">
            {pokemon.types?.map((t) => <TypeChip key={t} type={t} />)}
          </div>
        </div>
      </div>
    </motion.button>
  );
}
