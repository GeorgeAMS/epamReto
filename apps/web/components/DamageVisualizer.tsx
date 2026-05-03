"use client";

import { motion } from "framer-motion";
import { pokemonNameToId } from "@/lib/pokemon-utils";
import { PokemonSprite } from "./PokemonSprite";

export type DamageParse = {
  low: number;
  high: number;
  pctLow?: number;
  pctHigh?: number;
};

/** Extrae rango de daño y % HP del markdown del calculator_agent. */
export function parseDamageFromText(text: string): DamageParse | null {
  const range = text.match(/(\d+)\s*[–-]\s*(\d+)\s+de daño/i);
  if (!range) return null;
  const low = parseInt(range[1], 10);
  const high = parseInt(range[2], 10);
  const pct = text.match(/\((\d+(?:\.\d+)?)%\s*[–-]\s*(\d+(?:\.\d+)?)%/i);
  const pctLow = pct ? parseFloat(pct[1]) : undefined;
  const pctHigh = pct ? parseFloat(pct[2]) : undefined;
  return { low, high, pctLow, pctHigh };
}

export function DamageVisualizer({
  attacker,
  defender,
  move,
  damageRange,
  maxHP,
  effectiveness,
  text,
  maxHpFallback = 100,
}: {
  attacker?: { id: number; name: string };
  defender?: { id: number; name: string };
  move?: string;
  damageRange?: [number, number];
  maxHP?: number;
  effectiveness?: number;
  text?: string;
  maxHpFallback?: number;
}) {
  const parsed = text ? parseDamageFromText(text) : null;
  const fallbackRange = parsed ? ([parsed.low, parsed.high] as [number, number]) : null;
  const finalRange = damageRange ?? fallbackRange;
  const guessAttacker = text?.match(/^\s*([A-Za-z-]+)\s+/)?.[1] ?? "attacker";
  const guessDefender = text?.match(/\s([A-Za-z-]+)\s+takes/i)?.[1] ?? "defender";
  const inferredAttacker = attacker ?? { name: guessAttacker, id: pokemonNameToId(guessAttacker) ?? 25 };
  const inferredDefender = defender ?? { name: guessDefender, id: pokemonNameToId(guessDefender) ?? 6 };

  if (!finalRange) return null;

  const [minDamage, maxDamage] = finalRange;
  const hp = maxHP ?? maxHpFallback;
  const eff = effectiveness ?? 1;
  const percentMin = (minDamage / hp) * 100;
  const percentMax = (maxDamage / hp) * 100;
  const remainingHpPct = Math.max(0, 100 - percentMax);

  return (
    <div className="my-4 rounded-lg border border-arcana-border bg-gray-800 p-6">
      <div className="mb-6 flex items-center justify-between gap-3">
        <div className="text-center">
          <PokemonSprite pokemonId={inferredAttacker.id} pokemonName={inferredAttacker.name} size="md" variant="artwork" />
          <p className="mt-2 text-sm capitalize">{inferredAttacker.name}</p>
        </div>
        <div className="mx-4 flex-1 text-center">
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            className="mb-2 text-2xl font-bold text-[color:var(--pokedex-yellow)]"
          >
            {move || "Damage Calc"}
          </motion.div>
          <div className="text-sm text-gray-400">
            {eff > 1 ? "It's super effective!" : eff < 1 ? "It's not very effective..." : "Normal effectiveness"}
          </div>
        </div>
        <div className="text-center">
          <PokemonSprite pokemonId={inferredDefender.id} pokemonName={inferredDefender.name} size="md" variant="artwork" />
          <p className="mt-2 text-sm capitalize">{inferredDefender.name}</p>
        </div>
      </div>

      <div className="relative h-8 overflow-hidden rounded-full bg-gray-700">
        <motion.div
          initial={{ width: "100%" }}
          animate={{ width: `${remainingHpPct}%` }}
          transition={{ duration: 1, ease: "easeOut" }}
          className="absolute left-0 top-0 h-full bg-green-500"
        />
        <div className="absolute inset-0 flex items-center justify-center text-sm font-bold text-zinc-100">HP</div>
      </div>

      <motion.div
        initial={{ opacity: 0, y: -20, scale: 0.9 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ delay: 0.3, type: "spring", stiffness: 240, damping: 14 }}
        className="mt-4 text-center"
      >
        <span className="text-3xl font-bold text-red-500">
          {minDamage}-{maxDamage}
        </span>
        <span className="ml-2 text-lg text-gray-400">
          ({percentMin.toFixed(1)}-{percentMax.toFixed(1)}%)
        </span>
      </motion.div>
    </div>
  );
}
