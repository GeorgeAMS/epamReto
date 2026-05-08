import { createFileRoute } from "@tanstack/react-router";
import { requireAuth } from "@/lib/route-guards";
import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { api, normalizeGenerationList, normalizePokemonList, normalizeStringList } from "@/lib/api/client";
import type { Pokemon, PokemonType } from "@/lib/api/types";
import { PokemonCard } from "@/components/pokemon/PokemonCard";
import { PokemonModal } from "@/components/pokemon/PokemonModal";
import { TypeChip } from "@/components/pokemon/TypeChip";
import { Search, X } from "lucide-react";

export const Route = createFileRoute("/explore")({
  beforeLoad: requireAuth,
  head: () => ({
    meta: [
      { title: "Pokédex — Pokédex Arcana" },
      { name: "description", content: "Explora todos los Pokémon con filtros por tipo y generación." },
    ],
  }),
  component: ExplorePage,
});

function ExplorePage() {
  const [search, setSearch] = useState("");
  const [type, setType] = useState<string | "">("");
  const [gen, setGen] = useState<string | "">("");
  const [selected, setSelected] = useState<Pokemon | null>(null);

  const typesQ = useQuery({ queryKey: ["pokedex/types"], queryFn: api.pokedexTypes });
  const gensQ = useQuery({ queryKey: ["pokedex/generations"], queryFn: api.pokedexGenerations });
  const listQ = useQuery({
    queryKey: ["pokedex/list", { type, gen, search }],
    queryFn: () => api.pokedexList({ type: type || undefined, generation: gen || undefined, search: search || undefined, limit: 60 }),
  });

  const types = useMemo(() => normalizeStringList(typesQ.data, "types") as PokemonType[], [typesQ.data]);
  const gens = useMemo(() => normalizeGenerationList(gensQ.data), [gensQ.data]);
  const list = useMemo(() => normalizePokemonList(listQ.data), [listQ.data]);

  return (
    <div className="mx-auto max-w-7xl px-4 py-6">
      <header className="mb-5">
        <div className="font-pixel text-[10px] text-poke-blue uppercase">Pokédex Nacional</div>
        <h1 className="font-display text-3xl sm:text-4xl font-bold tracking-tight text-poke-black mt-1">
          Explora la <span className="text-poke-red">Pokédex</span>
        </h1>
      </header>

      <div className="sticky top-[4.5rem] z-30 -mx-4 px-4 py-3 mb-5 bg-poke-cream/95 backdrop-blur-md border-y-[3px] border-poke-black">
        <div className="flex flex-col gap-3">
          <div className="relative">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-4 w-4 text-poke-black/60" strokeWidth={3} />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Buscar Pokémon… (Pikachu, Garchomp…)"
              className="w-full rounded-full bg-poke-white border-[3px] border-poke-black pl-11 pr-10 py-2.5 text-sm font-medium placeholder:text-poke-black/40 focus:outline-none focus:bg-poke-yellow/20 shadow-[0_3px_0_0_var(--poke-black)] transition-colors"
            />
            {search && (
              <button onClick={() => setSearch("")} className="absolute right-3 top-1/2 -translate-y-1/2 grid place-items-center h-6 w-6 rounded-full bg-poke-black text-poke-white"><X className="h-3 w-3" strokeWidth={3} /></button>
            )}
          </div>

          {types.length > 0 && (
            <div className="flex gap-2 overflow-x-auto scrollbar-thin pb-1">
              <FilterChip active={!type} onClick={() => setType("")} label="Todos" />
              {types.map((t) => (
                <button key={t} onClick={() => setType(type === t ? "" : t)} className={`shrink-0 transition-transform ${type === t ? "scale-110 -translate-y-0.5" : "opacity-70 hover:opacity-100"}`}>
                  <TypeChip type={t} />
                </button>
              ))}
            </div>
          )}

          {gens.length > 0 && (
            <div className="flex gap-2 overflow-x-auto scrollbar-thin">
              <FilterChip active={!gen} onClick={() => setGen("")} label="Todas las gens" />
              {gens.map((g) => (
                <FilterChip key={g.id} active={gen === g.id} onClick={() => setGen(gen === g.id ? "" : g.id)} label={g.label} />
              ))}
            </div>
          )}
        </div>
      </div>

      {listQ.isLoading ? (
        <Grid>{Array.from({ length: 12 }).map((_, i) => <div key={i} className="h-56 skeleton" />)}</Grid>
      ) : listQ.isError ? (
        <ErrorState message={(listQ.error as Error)?.message} onRetry={() => listQ.refetch()} />
      ) : list.length === 0 ? (
        <EmptyState />
      ) : (
        <Grid>{list.map((p) => <PokemonCard key={p.id ?? p.name} pokemon={p} onClick={setSelected} />)}</Grid>
      )}

      <PokemonModal pokemon={selected} onClose={() => setSelected(null)} />
    </div>
  );
}

function Grid({ children }: { children: React.ReactNode }) {
  return <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">{children}</div>;
}
function FilterChip({ active, onClick, label }: { active: boolean; onClick: () => void; label: string }) {
  return (
    <button onClick={onClick} className={`shrink-0 rounded-full px-3 py-1 text-xs font-bold border-2 border-poke-black transition-all shadow-[0_2px_0_0_var(--poke-black)] ${active ? "bg-poke-red text-poke-white -translate-y-0.5 shadow-[0_3px_0_0_var(--poke-black)]" : "bg-poke-white text-poke-black hover:bg-poke-yellow"}`}>{label}</button>
  );
}
function EmptyState() {
  return (
    <div className="text-center py-16">
      <div className="text-5xl mb-3">🔍</div>
      <h3 className="font-display text-xl font-bold text-poke-black">¡No hay Pokémon!</h3>
      <p className="text-sm text-poke-black/70 mt-1 font-medium">Prueba con otra búsqueda o limpia los filtros.</p>
    </div>
  );
}
function ErrorState({ message, onRetry }: { message?: string; onRetry: () => void }) {
  return (
    <div className="poke-panel p-6 text-center max-w-md mx-auto">
      <h3 className="font-display text-lg font-bold text-poke-red">¡Conexión interrumpida!</h3>
      <p className="text-xs text-poke-black/70 mt-1 break-all font-medium">{message}</p>
      <button onClick={onRetry} className="mt-3 poke-btn bg-poke-red text-poke-white px-4 py-1.5 text-xs">Reintentar</button>
    </div>
  );
}


