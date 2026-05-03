"use client";

import Image from "next/image";
import { useMemo, useState } from "react";
import { getPokemonArtwork, getPokemonSpriteUrl } from "@/lib/pokemon-utils";

interface PokemonSpriteProps {
  pokemonId: number;
  pokemonName?: string;
  size?: "sm" | "md" | "lg" | "xl";
  variant?: "sprite" | "artwork";
  className?: string;
}

const SIZE_MAP = {
  sm: 48,
  md: 96,
  lg: 128,
  xl: 256,
} as const;

export function PokemonSprite({
  pokemonId,
  pokemonName,
  size = "md",
  variant = "sprite",
  className = "",
}: PokemonSpriteProps) {
  const [error, setError] = useState(false);
  const dimensions = SIZE_MAP[size];
  const imageUrl = useMemo(
    () => (variant === "artwork" ? getPokemonArtwork(pokemonId) : getPokemonSpriteUrl(pokemonId)),
    [pokemonId, variant],
  );

  if (error) {
    return (
      <div
        className={`flex items-center justify-center rounded-lg bg-gray-800 ${className}`}
        style={{ width: dimensions, height: dimensions }}
      >
        <svg viewBox="0 0 96 96" className="text-gray-600" width={dimensions} height={dimensions}>
          <circle cx="48" cy="48" r="40" fill="currentColor" opacity="0.2" />
          <text x="48" y="58" textAnchor="middle" fontSize="32" fill="currentColor">
            ?
          </text>
        </svg>
      </div>
    );
  }

  return (
    <div className={`relative ${className}`} style={{ width: dimensions, height: dimensions }}>
      <Image
        src={imageUrl}
        alt={pokemonName || `Pokemon #${pokemonId}`}
        width={dimensions}
        height={dimensions}
        className="pixelated object-contain"
        onError={() => setError(true)}
        unoptimized
      />
    </div>
  );
}
