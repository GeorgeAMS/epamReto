"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useMemo, useState } from "react";
import { PokemonSprite } from "@/components/PokemonSprite";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { pokemonNameToId, TYPE_COLORS } from "@/lib/pokemon-utils";
import { cn } from "@/lib/utils";
import {
  heatmapClass,
  POKEMON_TYPES,
  teamCoverageMatrix,
  type PokemonType,
} from "@/lib/typeChart";

const SLOTS = 6;

export function TeamBuilder() {
  const [names, setNames] = useState<string[]>(() => Array(SLOTS).fill(""));
  const [typesPerSlot, setTypesPerSlot] = useState<PokemonType[][]>(() =>
    Array.from({ length: SLOTS }, () => []),
  );

  const matrix = useMemo(
    () => teamCoverageMatrix(typesPerSlot),
    [typesPerSlot],
  );

  const toggleType = (slot: number, t: PokemonType) => {
    setTypesPerSlot((prev) => {
      const next = prev.map((row) => [...row]);
      const row = next[slot];
      const i = row.indexOf(t);
      if (i >= 0) row.splice(i, 1);
      else if (row.length < 2) row.push(t);
      return next;
    });
  };

  return (
    <Card className="border-arcana-border/80">
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Team Builder</CardTitle>
        <p className="text-xs text-arcana-muted">
          Hasta 2 tipos por slot. Heatmap: mejor cobertura STAB del equipo vs cada tipo
          defensor.
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-2 md:grid-cols-3 lg:grid-cols-6">
          {Array.from({ length: SLOTS }).map((_, slot) => {
            const name = names[slot];
            const pokemonId = name.trim() ? pokemonNameToId(name.trim()) : null;
            return (
              <motion.div
                key={slot}
                layout
                className="rounded-lg border border-arcana-border bg-gradient-to-b from-arcana-bg/90 to-zinc-900 p-2"
              >
                <p className="mb-1 text-center font-mono text-[10px] text-arcana-muted">
                  #{slot + 1}
                </p>
                <div className="relative mx-auto mb-2 aspect-square w-full max-w-[88px] overflow-hidden rounded-md bg-zinc-900">
                  <AnimatePresence mode="wait">
                    {pokemonId ? (
                      <motion.div
                        key={pokemonId}
                        initial={{ opacity: 0, scale: 0.92 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0 }}
                        className="flex h-full w-full items-center justify-center"
                      >
                        <PokemonSprite
                          pokemonId={pokemonId}
                          pokemonName={name}
                          size="md"
                          variant="artwork"
                          className="h-[88px] w-[88px]"
                        />
                      </motion.div>
                    ) : (
                      <div className="flex h-full items-center justify-center text-[10px] text-arcana-muted">
                        escribe nombre
                      </div>
                    )}
                  </AnimatePresence>
                </div>
                <Input
                  placeholder="Nombre"
                  value={name}
                  onChange={(e) => {
                    const v = e.target.value;
                    setNames((prev) => {
                      const n = [...prev];
                      n[slot] = v;
                      return n;
                    });
                  }}
                  className="h-8 text-xs"
                />
                <div className="mt-2 flex max-h-24 flex-wrap gap-0.5 overflow-y-auto">
                  {POKEMON_TYPES.map((t) => {
                    const on = typesPerSlot[slot].includes(t);
                    return (
                      <button
                        key={t}
                        type="button"
                        title={t}
                        onClick={() => toggleType(slot, t)}
                        className={cn(
                          "rounded px-1 py-0 font-mono text-[9px] uppercase",
                          on
                            ? "text-zinc-950"
                            : "bg-zinc-800/80 text-zinc-500 hover:text-zinc-300",
                        )}
                        style={on ? { backgroundColor: TYPE_COLORS[t] } : undefined}
                      >
                        {t.slice(0, 3)}
                      </button>
                    );
                  })}
                </div>
              </motion.div>
            );
          })}
        </div>

        <div className="overflow-x-auto rounded-lg border border-arcana-border p-2">
          <div className="flex gap-0.5">
            {POKEMON_TYPES.map((def) => (
              <div key={def} className="flex flex-col items-center gap-1">
                <span className="origin-left rotate-45 whitespace-nowrap font-mono text-[8px] uppercase text-arcana-muted">
                  {def.slice(0, 3)}
                </span>
                <div
                  className={cn(
                    "h-8 w-7 rounded-sm text-center font-mono text-[10px] leading-8",
                    heatmapClass(matrix[def]),
                  )}
                  title={`vs ${def}: ×${matrix[def].toFixed(2)}`}
                >
                  {matrix[def] >= 2 ? "2+" : matrix[def].toFixed(1)}
                </div>
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
