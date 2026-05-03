"use client";

import { useCallback, useEffect, useState } from "react";
import { FilterBar } from "@/components/FilterBar";
import { PokemonDetailModal } from "@/components/PokemonDetailModal";
import { PokemonGrid } from "@/components/PokemonGrid";
import { getApiBase } from "@/lib/api";

type PokemonListItem = {
  id: number;
  name: string;
  types: string[];
  sprite_url: string;
};

type Filters = {
  search: string;
  type: string | null;
  generation: number | null;
};

export default function ExplorePage() {
  const [pokemon, setPokemon] = useState<PokemonListItem[]>([]);
  const [selectedPokemon, setSelectedPokemon] = useState<number | null>(null);
  const [filters, setFilters] = useState<Filters>({
    search: "",
    type: null,
    generation: null,
  });
  const [loading, setLoading] = useState(true);

  const loadPokemon = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.append("limit", "100");

      if (filters.type) params.append("type", filters.type);
      if (filters.generation) params.append("generation", filters.generation.toString());
      if (filters.search) params.append("search", filters.search);

      const url = `${getApiBase()}/pokedex/pokemon?${params.toString()}`;
      console.log("Fetching:", url);

      const response = await fetch(url);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = (await response.json()) as PokemonListItem[];
      console.log("Received data:", data);
      setPokemon(data);
    } catch (error) {
      console.error("Error loading Pokemon:", error);
      setPokemon([]);
      const message = error instanceof Error ? error.message : String(error);
      alert(
        `Error cargando Pokemon: ${message}\n\nVerifica que el backend este corriendo en http://localhost:18000`,
      );
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    void loadPokemon();
  }, [loadPokemon]);

  return (
    <div className="space-y-6">
      <FilterBar filters={filters} onChange={setFilters} />

      {loading ? (
        <div className="py-12 text-center">
          <div className="mx-auto h-12 w-12 animate-spin rounded-full border-4 border-arcana-gold border-t-transparent" />
          <p className="mt-4 text-gray-400">Cargando Pokemon...</p>
        </div>
      ) : (
        <PokemonGrid pokemon={pokemon} onSelect={setSelectedPokemon} />
      )}

      {pokemon.length === 0 && !loading ? (
        <div className="py-12 text-center">
          <p className="mb-4 text-gray-400">No se pudieron cargar los Pokemon</p>
          <button
            onClick={() => void loadPokemon()}
            className="rounded bg-pokedex-yellow px-4 py-2 text-black hover:bg-yellow-500"
          >
            Reintentar
          </button>
        </div>
      ) : null}

      {selectedPokemon ? (
        <PokemonDetailModal pokemonId={selectedPokemon} onClose={() => setSelectedPokemon(null)} />
      ) : null}
    </div>
  );
}
