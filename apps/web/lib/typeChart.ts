/**
 * Tabla Gen VI–IX (misma codificación que domain/pokemon/services.py).
 * Solo entradas ≠ 1.0; el resto es neutro.
 */
const NVE = 0.5;
const SE = 2;
const NE = 0;

export const POKEMON_TYPES = [
  "normal",
  "fire",
  "water",
  "electric",
  "grass",
  "ice",
  "fighting",
  "poison",
  "ground",
  "flying",
  "psychic",
  "bug",
  "rock",
  "ghost",
  "dragon",
  "dark",
  "steel",
  "fairy",
] as const;

export type PokemonType = (typeof POKEMON_TYPES)[number];

const OVERRIDES: Partial<Record<PokemonType, Partial<Record<PokemonType, number>>>> = {
  normal: { rock: NVE, ghost: NE, steel: NVE },
  fire: {
    fire: NVE,
    water: NVE,
    grass: SE,
    ice: SE,
    bug: SE,
    rock: NVE,
    dragon: NVE,
    steel: SE,
  },
  water: {
    fire: SE,
    water: NVE,
    grass: NVE,
    ground: SE,
    rock: SE,
    dragon: NVE,
  },
  electric: {
    water: SE,
    electric: NVE,
    grass: NVE,
    ground: NE,
    flying: SE,
    dragon: NVE,
  },
  grass: {
    fire: NVE,
    water: SE,
    grass: NVE,
    poison: NVE,
    ground: SE,
    flying: NVE,
    bug: NVE,
    rock: SE,
    dragon: NVE,
    steel: NVE,
  },
  ice: {
    fire: NVE,
    water: NVE,
    grass: SE,
    ice: NVE,
    ground: SE,
    flying: SE,
    dragon: SE,
    steel: NVE,
  },
  fighting: {
    normal: SE,
    ice: SE,
    poison: NVE,
    flying: NVE,
    psychic: NVE,
    bug: NVE,
    rock: SE,
    ghost: NE,
    dark: SE,
    steel: SE,
    fairy: NVE,
  },
  poison: {
    grass: SE,
    poison: NVE,
    ground: NVE,
    rock: NVE,
    ghost: NVE,
    steel: NE,
    fairy: SE,
  },
  ground: {
    fire: SE,
    electric: SE,
    grass: NVE,
    poison: SE,
    flying: NE,
    bug: NVE,
    rock: SE,
    steel: SE,
  },
  flying: {
    electric: NVE,
    grass: SE,
    fighting: SE,
    bug: SE,
    rock: NVE,
    steel: NVE,
  },
  psychic: {
    fighting: SE,
    poison: SE,
    psychic: NVE,
    dark: NE,
    steel: NVE,
  },
  bug: {
    fire: NVE,
    grass: SE,
    fighting: NVE,
    poison: NVE,
    flying: NVE,
    psychic: SE,
    ghost: NVE,
    dark: SE,
    steel: NVE,
    fairy: NVE,
  },
  rock: {
    fire: SE,
    ice: SE,
    fighting: NVE,
    ground: NVE,
    flying: SE,
    bug: SE,
    steel: NVE,
  },
  ghost: {
    normal: NE,
    psychic: SE,
    ghost: SE,
    dark: NVE,
  },
  dragon: { dragon: SE, steel: NVE, fairy: NE },
  dark: {
    fighting: NVE,
    psychic: SE,
    ghost: SE,
    dark: NVE,
    fairy: NVE,
  },
  steel: {
    fire: NVE,
    water: NVE,
    electric: NVE,
    ice: SE,
    rock: SE,
    steel: NVE,
    fairy: SE,
  },
  fairy: {
    fire: NVE,
    fighting: SE,
    poison: NVE,
    dragon: SE,
    dark: SE,
    steel: NVE,
  },
};

export function typeMultiplier(attack: PokemonType, defense: PokemonType): number {
  return OVERRIDES[attack]?.[defense] ?? 1;
}

/** Mejor multiplicador STAB del miembro (uno o dos tipos) contra un tipo defensor. */
export function memberCoverage(types: PokemonType[], defend: PokemonType): number {
  if (types.length === 0) return 0;
  return Math.max(...types.map((t) => typeMultiplier(t, defend)));
}

/** Por cada tipo defensor: máximo del equipo (6 miembros). */
export function teamCoverageMatrix(
  members: PokemonType[][],
): Record<PokemonType, number> {
  const row: Partial<Record<PokemonType, number>> = {};
  for (const def of POKEMON_TYPES) {
    const vals = members.map((m) => memberCoverage(m, def));
    row[def] = vals.length ? Math.max(...vals) : 0;
  }
  return row as Record<PokemonType, number>;
}

/** Colores de celda para heatmap (ofensivo: qué tan bien cubre el equipo cada tipo). */
export function heatmapClass(mult: number): string {
  if (mult >= 2) return "bg-emerald-600/80 text-white";
  if (mult >= 1) return "bg-zinc-600/60 text-zinc-100";
  if (mult > 0) return "bg-amber-900/60 text-amber-100";
  return "bg-red-900/70 text-red-100";
}
