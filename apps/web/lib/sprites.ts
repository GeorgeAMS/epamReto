/** IDs oficiales PokéAPI para artwork (demo / hackathon). */
const IDS: Record<string, number> = {
  bulbasaur: 1,
  charmander: 4,
  squirtle: 7,
  pikachu: 25,
  jigglypuff: 39,
  gengar: 94,
  abomasnow: 460,
  dragonite: 149,
  garchomp: 445,
  dragapult: 887,
  lucario: 448,
  corviknight: 823,
  ferrothorn: 598,
  clefable: 36,
  tinkaton: 959,
  greattusk: 990,
};

export function officialArtUrl(name: string): string | null {
  const key = name
    .toLowerCase()
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .replace(/[^a-z]/g, "");
  const id = IDS[key];
  if (!id) return null;
  return `https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/${id}.png`;
}
