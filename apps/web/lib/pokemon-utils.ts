/**
 * Obtiene URL del sprite de un Pokémon desde GitHub.
 */
export function getPokemonSpriteUrl(pokemonId: number): string {
  return `https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/${pokemonId}.png`;
}

/**
 * Obtiene artwork oficial de alta calidad.
 */
export function getPokemonArtwork(pokemonId: number): string {
  return `https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/${pokemonId}.png`;
}

/**
 * Mapeo de nombres comunes a IDs (enfocado en demo).
 */
export const POKEMON_NAME_TO_ID: Record<string, number> = {
  bulbasaur: 1,
  ivysaur: 2,
  venusaur: 3,
  charmander: 4,
  charmeleon: 5,
  charizard: 6,
  squirtle: 7,
  wartortle: 8,
  blastoise: 9,
  pikachu: 25,
  raichu: 26,
  jigglypuff: 39,
  wigglytuff: 40,
  clefable: 36,
  gengar: 94,
  dragonite: 149,
  mewtwo: 150,
  mew: 151,
  steelix: 208,
  tyranitar: 248,
  blaziken: 257,
  salamence: 373,
  garchomp: 445,
  heatran: 485,
  abomasnow: 460,
  ferrothorn: 598,
  toxapex: 748,
  corviknight: 823,
  dragapult: 887,
  tinkaton: 959,
};

/**
 * Convierte nombre a ID.
 */
export function pokemonNameToId(name: string): number | null {
  const normalized = name
    .toLowerCase()
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .replace(/[^a-z0-9-]/g, "");
  return POKEMON_NAME_TO_ID[normalized] ?? null;
}

/**
 * Colores por tipo de Pokémon.
 */
export const TYPE_COLORS: Record<string, string> = {
  normal: "#A8A878",
  fire: "#F08030",
  water: "#6890F0",
  electric: "#F8D030",
  grass: "#78C850",
  ice: "#98D8D8",
  fighting: "#C03028",
  poison: "#A040A0",
  ground: "#E0C068",
  flying: "#A890F0",
  psychic: "#F85888",
  bug: "#A8B820",
  rock: "#B8A038",
  ghost: "#705898",
  dragon: "#7038F8",
  dark: "#705848",
  steel: "#B8B8D0",
  fairy: "#EE99AC",
};
