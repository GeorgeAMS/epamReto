import type { Pokemon, PokemonStats } from "@/lib/api/types";
import { api } from "@/lib/api/client";
import { TypeChip } from "./TypeChip";
import { motion, AnimatePresence } from "framer-motion";
import { X } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";

const fallback = (id: number) => `https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/${id}.png`;

const STAT_ORDER: { key: keyof PokemonStats; label: string }[] = [
  { key: "hp", label: "HP" },
  { key: "attack", label: "ATK" },
  { key: "defense", label: "DEF" },
  { key: "special_attack", label: "AT. ESP." },
  { key: "special_defense", label: "DEF. ESP." },
  { key: "speed", label: "VEL." },
];

/** El listado no trae stats; el detalle usa claves PokéAPI con guión o snake. */
function statsFromApi(raw: Record<string, number> | undefined | null): PokemonStats | undefined {
  if (!raw) return undefined;
  const v = (hyphen: string, snake: keyof PokemonStats) => raw[snake] ?? raw[hyphen];
  const hp = v("hp", "hp");
  if (hp === undefined) return undefined;
  return {
    hp,
    attack: v("attack", "attack") ?? 0,
    defense: v("defense", "defense") ?? 0,
    special_attack: v("special-attack", "special_attack") ?? 0,
    special_defense: v("special-defense", "special_defense") ?? 0,
    speed: v("speed", "speed") ?? 0,
  };
}

function mergePokemon(base: Pokemon, detail: Record<string, unknown> | undefined): Pokemon {
  if (!detail) return base;
  const stats = statsFromApi(detail.stats as Record<string, number> | undefined);
  return {
    ...base,
    name: (detail.name as string) ?? base.name,
    types: (detail.types as Pokemon["types"]) ?? base.types,
    stats: stats ?? base.stats,
    abilities: (detail.abilities as string[]) ?? base.abilities,
    height: (detail.height as number) ?? base.height,
    weight: (detail.weight as number) ?? base.weight,
    sprite: (detail.sprite_url as string) ?? base.sprite,
    artwork: (detail.artwork_url as string) ?? base.artwork,
    generation: (detail.generation as number) ?? base.generation,
  };
}

export function PokemonModal({ pokemon, onClose }: { pokemon: Pokemon | null; onClose: () => void }) {
  const id = pokemon?.id;
  const detailQ = useQuery({
    queryKey: ["pokedex/pokemon", id],
    queryFn: () => api.pokemonDetail(id!),
    enabled: !!pokemon && typeof id === "number",
    staleTime: 5 * 60 * 1000,
  });

  const display = useMemo(() => (pokemon ? mergePokemon(pokemon, detailQ.data as Record<string, unknown> | undefined) : null), [pokemon, detailQ.data]);

  return (
    <AnimatePresence>
      {pokemon && display && (
        <motion.div
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
          onClick={onClose}
          className="fixed inset-0 z-50 grid place-items-center bg-poke-black/60 backdrop-blur-sm p-4"
        >
          <motion.div
            initial={{ y: 20, opacity: 0, scale: 0.95 }} animate={{ y: 0, opacity: 1, scale: 1 }} exit={{ y: 20, opacity: 0 }}
            onClick={(e) => e.stopPropagation()}
            className="relative w-full max-w-lg poke-panel overflow-hidden"
          >
            {/* Header rojo Pokédex */}
            <div className="bg-poke-red px-5 py-3 border-b-[3px] border-poke-black flex items-center gap-3">
              <div className="h-4 w-4 rounded-full bg-poke-blue border-2 border-poke-black ring-2 ring-poke-white" />
              <div className="flex gap-1.5">
                <span className="h-2 w-2 rounded-full bg-poke-red-dark border border-poke-black" />
                <span className="h-2 w-2 rounded-full bg-poke-yellow border border-poke-black" />
                <span className="h-2 w-2 rounded-full bg-emerald-500 border border-poke-black" />
              </div>
              <div className="ml-auto font-pixel text-[8px] text-poke-white">N°{String(display.id).padStart(3, "0")}</div>
              <button onClick={onClose} className="grid place-items-center h-7 w-7 rounded-full bg-poke-white border-2 border-poke-black hover:bg-poke-yellow"><X className="h-3.5 w-3.5 text-poke-black" strokeWidth={3} /></button>
            </div>

            <div className="p-6">
              <div className="flex flex-col items-center text-center">
                <div className="relative">
                  <div className="absolute inset-0 blur-2xl bg-poke-yellow/40 rounded-full" />
                  <img src={display.artwork ?? display.sprite ?? fallback(display.id)} alt={display.name} className="relative h-44 w-44 object-contain drop-shadow-[4px_8px_0_rgba(0,0,0,0.35)] float" />
                </div>
                <h2 className="font-display text-3xl font-bold capitalize mt-2 text-poke-black">{display.name}</h2>
                <div className="mt-2 flex gap-1.5">{display.types?.map((t) => <TypeChip key={t} type={t} />)}</div>
              </div>

              {detailQ.isLoading && !display.stats && (
                <div className="mt-6 rounded-xl border-2 border-dashed border-poke-black/30 bg-poke-cream/50 p-4 text-center font-pixel text-[9px] text-poke-black/60">
                  Cargando stats…
                </div>
              )}

              {display.stats && (
                <div className="mt-6 space-y-2 bg-poke-cream rounded-xl border-2 border-poke-black p-3 shadow-[0_3px_0_0_var(--poke-black)]">
                  {STAT_ORDER.map(({ key, label }) => {
                    const v = display.stats![key];
                    return (
                      <div key={key} className="flex items-center gap-3">
                        <span className="w-14 shrink-0 font-pixel text-[9px] text-poke-black">{label}</span>
                        <div className="flex-1 h-3 rounded-full bg-poke-white border-2 border-poke-black overflow-hidden">
                          <div className="h-full bg-gradient-to-r from-emerald-400 via-poke-yellow to-poke-red" style={{ width: `${Math.min(100, (v / 255) * 100)}%` }} />
                        </div>
                        <span className="w-9 shrink-0 text-right font-display text-base font-bold tabular-nums text-poke-black">{v}</span>
                      </div>
                    );
                  })}
                </div>
              )}

              {detailQ.isError && !display.stats && (
                <p className="mt-4 text-center text-xs font-medium text-poke-red">No se pudieron cargar las stats.</p>
              )}

              {(display.abilities?.length || display.height || display.weight) && (
                <div className="mt-4 grid grid-cols-3 gap-2">
                  {display.abilities?.length ? <Box label="HABILIDADES" value={display.abilities.join(", ")} /> : null}
                  {display.height ? <Box label="ALTURA" value={`${display.height} m`} /> : null}
                  {display.weight ? <Box label="PESO" value={`${display.weight} kg`} /> : null}
                </div>
              )}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

function Box({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-lg bg-poke-cream border-2 border-poke-black p-2 text-center shadow-[0_2px_0_0_var(--poke-black)]">
      <div className="font-pixel text-[8px] text-poke-black/70 tracking-wider">{label}</div>
      <div className="text-xs font-bold mt-0.5 truncate capitalize text-poke-black">{value}</div>
    </div>
  );
}
