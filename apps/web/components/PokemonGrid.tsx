"use client";

import { PokemonCard } from "./PokemonCard";

interface Pokemon {
  id: number;
  name: string;
  types: string[];
  sprite_url: string;
}

export function PokemonGrid({
  pokemon,
  onSelect,
}: {
  pokemon: Pokemon[];
  onSelect: (id: number) => void;
}) {
  return (
    <div className="grid grid-cols-2 gap-4 md:grid-cols-4 lg:grid-cols-6">
      {pokemon.map((p) => (
        <PokemonCard key={p.id} pokemon={p} onClick={() => onSelect(p.id)} />
      ))}
    </div>
  );
}
