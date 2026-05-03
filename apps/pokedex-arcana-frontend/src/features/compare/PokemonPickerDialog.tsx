import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, normalizePokemonList } from "@/lib/api/client";
import type { Pokemon } from "@/lib/api/types";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Search } from "lucide-react";
import { TypeChip } from "@/components/pokemon/TypeChip";

function normalizeListSprites(items: Pokemon[]): Pokemon[] {
  return items.map((p) => ({
    ...p,
    sprite: p.sprite ?? (p as { sprite_url?: string }).sprite_url,
    artwork: p.artwork ?? (p as { artwork_url?: string }).artwork_url,
  }));
}

type Props = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onPick: (pokemon: Pokemon) => void;
  /** Slugs ya usados en otros slots (evita duplicados). */
  excludeSlugs: string[];
};

export function PokemonPickerDialog({ open, onOpenChange, onPick, excludeSlugs }: Props) {
  const [search, setSearch] = useState("");
  const listQ = useQuery({
    queryKey: ["pokedex/list", "picker", search],
    queryFn: () => api.pokedexList({ search: search.trim() || undefined, limit: 72 }),
    enabled: open,
  });

  const list = useMemo(() => {
    const raw = normalizePokemonList(listQ.data);
    return normalizeListSprites(raw);
  }, [listQ.data]);

  const exclude = useMemo(() => new Set(excludeSlugs.map((s) => s.toLowerCase())), [excludeSlugs]);

  function handlePick(p: Pokemon) {
    const slug = p.name.toLowerCase();
    if (exclude.has(slug)) return;
    onPick(p);
    onOpenChange(false);
    setSearch("");
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[88vh] max-w-3xl border-[3px] border-poke-black bg-poke-cream p-0 gap-0 overflow-hidden shadow-[0_8px_0_0_var(--poke-black)]">
        <DialogHeader className="px-5 pt-5 pb-3 border-b-[3px] border-poke-black bg-poke-red text-poke-white">
          <DialogTitle className="font-display text-xl">Pokédex — elegir Pokémon</DialogTitle>
          <DialogDescription className="text-poke-white/90 text-sm font-medium">
            Toca un Pokémon para asignarlo al hueco. Los ya elegidos en otros huecos no aparecen activos si los filtras por nombre.
          </DialogDescription>
        </DialogHeader>

        <div className="px-4 py-3 border-b-2 border-poke-black/20 bg-poke-white">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-poke-black/50" strokeWidth={2.5} />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Buscar por nombre…"
              className="w-full rounded-full border-2 border-poke-black bg-poke-cream/50 py-2 pl-10 pr-4 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-poke-blue"
            />
          </div>
        </div>

        <ScrollArea className="h-[min(60vh,480px)] w-full">
          <div className="p-4">
            {listQ.isLoading ? (
              <div className="grid grid-cols-3 sm:grid-cols-4 gap-2">
                {Array.from({ length: 12 }).map((_, i) => (
                  <div key={i} className="aspect-square rounded-xl skeleton border-2 border-poke-black/20" />
                ))}
              </div>
            ) : listQ.isError ? (
              <p className="text-center text-sm text-poke-red font-medium">No se pudo cargar la lista.</p>
            ) : list.length === 0 ? (
              <p className="text-center text-sm text-poke-black/60 font-medium">Sin resultados. Prueba otro nombre.</p>
            ) : (
              <div className="grid grid-cols-3 sm:grid-cols-4 gap-2">
                {list.map((p) => {
                  const taken = exclude.has(p.name.toLowerCase());
                  return (
                    <button
                      key={`${p.id}-${p.name}`}
                      type="button"
                      disabled={taken}
                      onClick={() => handlePick(p)}
                      className={`flex flex-col items-center rounded-xl border-2 border-poke-black bg-poke-white p-2 text-center shadow-[0_3px_0_0_var(--poke-black)] transition-transform ${
                        taken ? "opacity-40 cursor-not-allowed" : "hover:-translate-y-0.5 active:scale-[0.98]"
                      }`}
                    >
                      <div className="relative h-16 w-full grid place-items-center">
                        {p.sprite || p.id ? (
                          <img
                            src={p.sprite ?? `https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/${p.id}.png`}
                            alt=""
                            className="max-h-16 max-w-full object-contain"
                            loading="lazy"
                          />
                        ) : (
                          <div className="h-14 w-14 skeleton rounded-lg" />
                        )}
                      </div>
                      <span className="mt-1 font-display text-[11px] font-bold capitalize leading-tight text-poke-black line-clamp-2">{p.name}</span>
                      <div className="mt-1 flex flex-wrap justify-center gap-0.5">
                        {p.types?.slice(0, 2).map((t) => (
                          <TypeChip key={t} type={t} className="text-[8px] px-1 py-0" />
                        ))}
                      </div>
                      {taken ? <span className="font-pixel text-[7px] text-poke-red mt-0.5">YA EN USO</span> : null}
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        </ScrollArea>
      </DialogContent>
    </Dialog>
  );
}
