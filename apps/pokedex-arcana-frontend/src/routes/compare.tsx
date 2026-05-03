import { createFileRoute } from "@tanstack/react-router";
import { useCallback, useEffect, useMemo, useState } from "react";
import { api, ApiError } from "@/lib/api/client";
import type { Pokemon } from "@/lib/api/types";
import { Button } from "@/components/ui/button";
import { TypeChip } from "@/components/pokemon/TypeChip";
import { PokemonPickerDialog } from "@/features/compare/PokemonPickerDialog";
import { Plus, X } from "lucide-react";
import { Legend, PolarAngleAxis, PolarGrid, PolarRadiusAxis, Radar, RadarChart, ResponsiveContainer, Tooltip } from "recharts";

export const Route = createFileRoute("/compare")({
  head: () => ({
    meta: [
      { title: "Comparar — Pokédex Arcana" },
      { name: "description", content: "Compara stats base de 2 a 4 Pokémon." },
    ],
  }),
  component: ComparePage,
});

const SLOT_COUNT = 4;

type Mon = {
  name: string;
  types: string[];
  base_stats: Record<string, number>;
  sprite: string;
  ability: string;
};

type CompareResult = {
  pokemon: Mon[];
  matchups: Record<string, { stat_advantages: string; type_advantages: string; summary: string }>;
  winner: string | null;
};

const STAT_ROWS: readonly { key: string; label: string }[] = [
  { key: "hp", label: "PS" },
  { key: "attack", label: "Ataque" },
  { key: "defense", label: "Defensa" },
  { key: "special_attack", label: "At. Esp." },
  { key: "special_defense", label: "Def. Esp." },
  { key: "speed", label: "Velocidad" },
  { key: "total", label: "Total" },
];

const RADAR_STATS: readonly { key: string; label: string }[] = [
  { key: "hp", label: "HP" },
  { key: "attack", label: "ATK" },
  { key: "defense", label: "DEF" },
  { key: "special_attack", label: "ATK ESP" },
  { key: "special_defense", label: "DEF ESP" },
  { key: "speed", label: "VEL" },
];

const RADAR_COLORS = ["#dc2626", "#2563eb", "#059669", "#7c3aed"] as const;

function displayName(slug: string) {
  return slug.replace(/-/g, " ");
}

function slotSprite(p: Pokemon) {
  return (
    p.sprite ??
    (p as { sprite_url?: string }).sprite_url ??
    (p.id ? `https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/${p.id}.png` : undefined)
  );
}

function CompareRadar({ pokemon }: { pokemon: Mon[] }) {
  const domainMax = useMemo(() => {
    let m = 0;
    for (const p of pokemon) {
      for (const { key } of RADAR_STATS) {
        m = Math.max(m, p.base_stats[key] ?? 0);
      }
    }
    return Math.min(255, Math.max(80, Math.ceil(m / 20) * 20));
  }, [pokemon]);

  const chartData = useMemo(() => {
    return RADAR_STATS.map(({ key, label }) => {
      const row: Record<string, string | number> = { stat: label };
      pokemon.forEach((p, i) => {
        row[`s${i}`] = p.base_stats[key] ?? 0;
      });
      return row;
    });
  }, [pokemon]);

  if (pokemon.length < 2) return null;

  return (
    <section className="mt-8">
      <h2 className="font-display text-lg font-bold text-poke-black">Desempeño (stats base)</h2>
      <p className="text-xs text-poke-black/65 mt-1 font-medium max-w-xl">
        Radar por stat: cada eje es un valor base (mismo máximo en todos los ejes para comparar forma, no “total” BST).
      </p>
      <div className="mt-4 rounded-2xl border-[3px] border-poke-black bg-poke-white p-4 shadow-[0_4px_0_0_var(--poke-black)]">
        <div className="h-[min(380px,55vw)] w-full min-h-[280px]">
          <ResponsiveContainer width="100%" height="100%">
            <RadarChart data={chartData} margin={{ top: 12, right: 28, bottom: 8, left: 28 }}>
              <PolarGrid stroke="#1a1a1a" strokeOpacity={0.25} />
              <PolarAngleAxis dataKey="stat" tick={{ fontSize: 10, fill: "#1a1a1a", fontWeight: 700 }} />
              <PolarRadiusAxis angle={18} domain={[0, domainMax]} tick={{ fontSize: 9 }} tickCount={4} />
              {pokemon.map((p, i) => (
                <Radar
                  key={p.name}
                  name={displayName(p.name)}
                  dataKey={`s${i}`}
                  stroke={RADAR_COLORS[i % RADAR_COLORS.length]}
                  fill={RADAR_COLORS[i % RADAR_COLORS.length]}
                  fillOpacity={0.18}
                  strokeWidth={2}
                />
              ))}
              <Legend wrapperStyle={{ fontSize: 12, fontWeight: 700 }} />
              <Tooltip
                contentStyle={{
                  borderRadius: 12,
                  border: "2px solid #1a1a1a",
                  fontWeight: 600,
                }}
              />
            </RadarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </section>
  );
}

function ComparePage() {
  const [slots, setSlots] = useState<(Pokemon | null)[]>(() => Array.from({ length: SLOT_COUNT }, () => null));
  const [pickerOpen, setPickerOpen] = useState(false);
  const [activeSlot, setActiveSlot] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<CompareResult | null>(null);

  const filledSlugs = useMemo(
    () => slots.filter((s): s is Pokemon => !!s).map((s) => s.name.toLowerCase()),
    [slots],
  );

  /** En el hueco activo se puede volver a elegir el mismo mon; en el resto no duplicar. */
  const excludeForPicker = useMemo(() => {
    if (activeSlot === null) return filledSlugs;
    return slots
      .map((s, i) => (s && i !== activeSlot ? s.name.toLowerCase() : null))
      .filter((x): x is string => x !== null);
  }, [slots, activeSlot, filledSlugs]);

  useEffect(() => {
    setData(null);
    setError(null);
  }, [slots]);

  const openPicker = useCallback((index: number) => {
    setActiveSlot(index);
    setPickerOpen(true);
  }, []);

  const assignSlot = useCallback((index: number, p: Pokemon | null) => {
    setSlots((prev) => {
      const next = [...prev];
      next[index] = p;
      return next;
    });
  }, []);

  const onPicked = useCallback(
    (p: Pokemon) => {
      if (activeSlot === null) return;
      assignSlot(activeSlot, p);
      setActiveSlot(null);
    },
    [activeSlot, assignSlot],
  );

  async function runCompare() {
    const names = filledSlugs;
    if (names.length < 2) {
      setError("Elige al menos 2 Pokémon en las tarjetas.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = (await api.comparePokemon(names)) as CompareResult;
      setData(res);
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : (err as Error)?.message ?? "Error";
      setError(msg);
      setData(null);
    } finally {
      setLoading(false);
    }
  }

  const canCompare = filledSlugs.length >= 2;

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <div className="font-pixel text-[10px] text-poke-blue uppercase">Análisis rápido</div>
      <h1 className="font-display text-3xl font-bold text-poke-black mt-1">
        Comparar <span className="text-poke-red">stats</span>
      </h1>
      <p className="mt-2 text-sm font-medium text-poke-black/70 max-w-2xl">
        Pulsa <strong className="text-poke-black">+</strong> en un hueco para abrir la <strong>Pokédex</strong> y elegir Pokémon (hasta 4). Luego <strong>Comparar</strong>.
      </p>

      <div className="mt-8 grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4">
        {slots.map((p, idx) => (
          <div key={idx} className="relative">
            {p ? (
              <div className="flex h-full min-h-[168px] flex-col rounded-2xl border-[3px] border-poke-black bg-poke-white p-3 shadow-[0_4px_0_0_var(--poke-black)]">
                <button
                  type="button"
                  onClick={() => assignSlot(idx, null)}
                  className="absolute right-2 top-2 grid h-8 w-8 place-items-center rounded-full border-2 border-poke-black bg-poke-cream text-poke-black hover:bg-poke-red hover:text-poke-white z-10"
                  aria-label="Quitar Pokémon"
                >
                  <X className="h-4 w-4" strokeWidth={3} />
                </button>
                <button
                  type="button"
                  onClick={() => openPicker(idx)}
                  className="flex flex-1 flex-col items-center justify-center text-center pt-1"
                >
                  <div className="h-20 w-full grid place-items-center">
                    <img
                      src={slotSprite(p)}
                      alt=""
                      className="max-h-20 max-w-full object-contain drop-shadow-[2px_4px_0_rgba(0,0,0,0.2)]"
                      loading="lazy"
                    />
                  </div>
                  <span className="mt-2 font-display text-sm font-bold capitalize text-poke-black leading-tight">{p.name}</span>
                  <div className="mt-1.5 flex flex-wrap justify-center gap-1">
                    {p.types?.map((t) => (
                      <TypeChip key={t} type={t} />
                    ))}
                  </div>
                  <span className="mt-2 font-pixel text-[8px] text-poke-blue">Cambiar</span>
                </button>
              </div>
            ) : (
              <button
                type="button"
                onClick={() => openPicker(idx)}
                className="flex min-h-[168px] w-full flex-col items-center justify-center gap-2 rounded-2xl border-[3px] border-dashed border-poke-black/50 bg-poke-cream/60 shadow-[0_3px_0_0_var(--poke-black)] transition-colors hover:border-poke-black hover:bg-poke-yellow/25"
              >
                <div className="grid h-14 w-14 place-items-center rounded-full border-[3px] border-poke-black bg-poke-white shadow-[0_2px_0_0_var(--poke-black)]">
                  <Plus className="h-7 w-7 text-poke-black" strokeWidth={3} />
                </div>
                <span className="font-pixel text-[9px] text-poke-black/70 uppercase">Hueco {idx + 1}</span>
              </button>
            )}
          </div>
        ))}
      </div>

      <div className="mt-6 flex flex-wrap items-center gap-3">
        <Button
          type="button"
          onClick={() => void runCompare()}
          disabled={loading || !canCompare}
          className="border-2 border-poke-black bg-poke-blue font-bold text-poke-white shadow-[0_3px_0_0_var(--poke-black)] hover:bg-poke-blue/90 disabled:opacity-50"
        >
          {loading ? "Comparando…" : "Comparar"}
        </Button>
        {!canCompare ? <span className="text-xs font-medium text-poke-black/55">Selecciona 2–4 Pokémon.</span> : null}
      </div>

      {error && (
        <p className="mt-4 rounded-xl border-2 border-poke-red bg-poke-white px-3 py-2 text-sm font-medium text-poke-red" role="alert">
          {error}
        </p>
      )}

      <PokemonPickerDialog
        open={pickerOpen}
        onOpenChange={(o) => {
          setPickerOpen(o);
          if (!o) setActiveSlot(null);
        }}
        onPick={onPicked}
        excludeSlugs={excludeForPicker}
      />

      {data && data.pokemon.length > 0 && (
        <div className="mt-10 space-y-8">
          {data.winner && (
            <div className="rounded-2xl border-[3px] border-poke-black bg-poke-yellow/90 px-4 py-3 shadow-[0_4px_0_0_var(--poke-black)]">
              <span className="font-pixel text-[9px] text-poke-black uppercase">Mayor BST</span>
              <div className="font-display text-xl font-bold capitalize text-poke-black mt-0.5">{displayName(data.winner)}</div>
            </div>
          )}

          <div className="overflow-x-auto rounded-2xl border-[3px] border-poke-black bg-poke-white shadow-[0_4px_0_0_var(--poke-black)]">
            <table className="w-full min-w-[520px] text-sm border-collapse">
              <thead>
                <tr className="border-b-2 border-poke-black bg-poke-cream">
                  <th className="p-3 text-left font-display font-bold text-poke-black w-28">Stat</th>
                  {data.pokemon.map((p) => (
                    <th key={p.name} className="p-3 text-center font-display font-bold text-poke-black border-l-2 border-poke-black/20 min-w-[120px]">
                      <div className="flex flex-col items-center gap-2">
                        {p.sprite ? (
                          <img src={p.sprite} alt="" className="h-16 w-16 object-contain" loading="lazy" />
                        ) : (
                          <div className="h-16 w-16 rounded-lg skeleton" />
                        )}
                        <span className="capitalize">{displayName(p.name)}</span>
                        <div className="flex flex-wrap justify-center gap-1">
                          {p.types.map((t) => (
                            <TypeChip key={t} type={t} />
                          ))}
                        </div>
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {STAT_ROWS.map((row) => (
                  <tr key={row.key} className="border-b border-poke-black/15 odd:bg-poke-cream/40">
                    <td className="p-2.5 font-bold text-poke-black/80">{row.label}</td>
                    {data.pokemon.map((p) => (
                      <td key={`${p.name}-${row.key}`} className="p-2.5 text-center font-mono font-bold border-l-2 border-poke-black/10">
                        {p.base_stats[row.key] ?? "—"}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {Object.keys(data.matchups).length > 0 && (
            <section>
              <h2 className="font-display text-lg font-bold text-poke-black">Resumen por pareja</h2>
              <ul className="mt-3 grid gap-3 sm:grid-cols-2">
                {Object.entries(data.matchups).map(([key, m]) => (
                  <li key={key} className="rounded-xl border-2 border-poke-black bg-poke-cream/80 p-3 shadow-[0_3px_0_0_var(--poke-black)]">
                    <div className="font-display font-bold text-poke-black capitalize text-sm">{key.replace(/_vs_/g, " vs ").replace(/-/g, " ")}</div>
                    <p className="text-xs text-poke-black/75 mt-2 font-medium leading-relaxed">
                      <span className="text-poke-blue font-bold">Stats:</span> {m.stat_advantages}
                    </p>
                    <p className="text-xs text-poke-black/75 mt-1 font-medium leading-relaxed">
                      <span className="text-poke-red font-bold">Tipos:</span> {m.type_advantages}
                    </p>
                    <p className="text-[11px] text-poke-black/60 mt-1">{m.summary}</p>
                  </li>
                ))}
              </ul>
            </section>
          )}

          <CompareRadar pokemon={data.pokemon} />
        </div>
      )}
    </div>
  );
}
