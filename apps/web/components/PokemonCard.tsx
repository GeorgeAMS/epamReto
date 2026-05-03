"use client";

import Image from "next/image";
import { TYPE_COLORS } from "@/lib/pokemon-utils";

interface Pokemon {
  id: number;
  name: string;
  types: string[];
  sprite_url: string;
}

export function PokemonCard({
  pokemon,
  onClick,
}: {
  pokemon: Pokemon;
  onClick: () => void;
}) {
  return (
    <div
      onClick={onClick}
      className="cursor-pointer rounded-lg bg-gray-800 p-4 transition-all hover:scale-105 hover:bg-gray-700"
    >
      <div className="relative mb-2 aspect-square w-full">
        <Image
          src={pokemon.sprite_url}
          alt={pokemon.name}
          fill
          className="pixelated object-contain"
          unoptimized
        />
      </div>

      <div className="mb-1 text-xs text-gray-500">#{pokemon.id.toString().padStart(4, "0")}</div>

      <div className="mb-2 font-bold capitalize">{pokemon.name}</div>

      <div className="flex gap-1">
        {pokemon.types.map((type) => (
          <span
            key={type}
            className="rounded px-2 py-1 text-xs"
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
  );
}
