import type { PokemonType } from "@/lib/api/types";
export function TypeChip({ type, className = "" }: { type: PokemonType | string; className?: string }) {
  return <span className={`type-chip type-${type} ${className}`}>{type}</span>;
}
