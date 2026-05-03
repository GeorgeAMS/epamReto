"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { getApiBase } from "@/lib/api";
import { TYPE_COLORS } from "@/lib/pokemon-utils";

type PokemonDetail = {
  id: number;
  name: string;
  artwork_url: string;
  types: string[];
  stats: Record<string, number>;
  abilities: string[];
  height: number;
  weight: number;
};

export function PokemonDetailModal({
  pokemonId,
  onClose,
}: {
  pokemonId: number;
  onClose: () => void;
}) {
  const [pokemon, setPokemon] = useState<PokemonDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetch(`${getApiBase()}/pokedex/pokemon/${pokemonId}`)
      .then((res) => res.json())
      .then((data: PokemonDetail) => {
        setPokemon(data);
        setLoading(false);
      });
  }, [pokemonId]);

  if (loading || !pokemon) {
    return (
      <Dialog open onOpenChange={onClose}>
        <DialogContent className="max-w-2xl">
          <div className="py-12 text-center">Cargando...</div>
        </DialogContent>
      </Dialog>
    );
  }

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-h-[90vh] max-w-4xl overflow-y-auto">
        <div className="grid gap-6 md:grid-cols-2">
          <div className="flex flex-col items-center">
            <div className="relative mb-4 h-64 w-64">
              <Image
                src={pokemon.artwork_url}
                alt={pokemon.name}
                fill
                className="object-contain"
                unoptimized
              />
            </div>

            <h2 className="mb-2 text-3xl font-bold capitalize">{pokemon.name}</h2>

            <div className="mb-4 text-gray-400">#{pokemon.id.toString().padStart(4, "0")}</div>

            <div className="mb-4 flex gap-2">
              {pokemon.types.map((type) => (
                <span
                  key={type}
                  className="rounded px-3 py-1 capitalize"
                  style={{
                    backgroundColor: TYPE_COLORS[type] || "#777",
                    color: "white",
                  }}
                >
                  {type}
                </span>
              ))}
            </div>
          </div>

          <div>
            <h3 className="mb-4 text-xl font-bold">Base Stats</h3>

            <div className="space-y-3">
              {Object.entries(pokemon.stats).map(([stat, value]) => (
                <div key={stat}>
                  <div className="mb-1 flex justify-between">
                    <span className="text-sm capitalize">{stat}</span>
                    <span className="font-bold">{value}</span>
                  </div>
                  <div className="h-2 w-full rounded-full bg-gray-700">
                    <div
                      className="h-2 rounded-full bg-arcana-gold"
                      style={{ width: `${(value / 255) * 100}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>

            <h3 className="mb-4 mt-6 text-xl font-bold">Abilities</h3>
            <ul className="space-y-2">
              {pokemon.abilities.map((ability) => (
                <li key={ability} className="text-sm capitalize">
                  - {ability.replace("-", " ")}
                </li>
              ))}
            </ul>

            <h3 className="mb-4 mt-6 text-xl font-bold">Physical</h3>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-gray-400">Height:</span>{" "}
                <span className="font-bold">{pokemon.height}m</span>
              </div>
              <div>
                <span className="text-gray-400">Weight:</span>{" "}
                <span className="font-bold">{pokemon.weight}kg</span>
              </div>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
