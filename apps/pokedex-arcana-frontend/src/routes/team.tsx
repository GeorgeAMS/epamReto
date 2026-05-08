import { createFileRoute } from "@tanstack/react-router";
import { requireAuth } from "@/lib/route-guards";
import { useState } from "react";
import { api, ApiError } from "@/lib/api/client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { TypeChip } from "@/components/pokemon/TypeChip";

export const Route = createFileRoute("/team")({
  beforeLoad: requireAuth,
  head: () => ({ meta: [{ title: "Equipo — Pokédex Arcana" }, { name: "description", content: "Constructor de equipos competitivos." }] }),
  component: TeamPage,
});

type TeamMember = {
  pokemon: string;
  types: string[];
  ability: string;
  item?: string | null;
  sprite: string;
  base_stats: Record<string, number>;
  role?: string | null;
};

type BuildResponse = {
  team: TeamMember[];
  weaknesses: Record<string, number>;
  resistances: Record<string, number>;
};

function TeamPage() {
  const [anchor, setAnchor] = useState("garchomp");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<BuildResponse | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    const name = anchor.trim();
    if (!name) return;
    setLoading(true);
    setError(null);
    try {
      const res = (await api.buildTeam({
        anchor_pokemon: name.toLowerCase().replace(/\s+/g, "-"),
        format: "OU",
        team_size: 6,
      })) as BuildResponse;
      setData(res);
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : (err as Error)?.message ?? "Error";
      setError(msg);
      setData(null);
    } finally {
      setLoading(false);
    }
  }

  const topWeak = data
    ? Object.entries(data.weaknesses)
        .filter(([, n]) => n >= 2)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 8)
    : [];

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      <h1 className="font-display text-3xl font-bold text-poke-black">
        Constructor de <span className="text-poke-red">Equipo</span>
      </h1>
      <p className="mt-2 text-sm font-medium text-poke-black/70">
        Borrador rápido alrededor de un Pokémon ancla (sugerencias de PokeAPI + cobertura de tipos). Para análisis fino usa el chat del Profesor Arcana.
      </p>

      <form onSubmit={onSubmit} className="mt-6 flex flex-col gap-3 rounded-2xl border-[3px] border-poke-black bg-poke-cream/80 p-4 shadow-[0_4px_0_0_var(--poke-black)] sm:flex-row sm:items-end">
        <div className="min-w-0 flex-1 space-y-1.5">
          <Label htmlFor="anchor" className="font-pixel text-[10px] uppercase text-poke-black">
            Pokémon ancla
          </Label>
          <Input
            id="anchor"
            value={anchor}
            onChange={(e) => setAnchor(e.target.value)}
            placeholder="ej. garchomp, dragapult…"
            className="border-2 border-poke-black bg-poke-white font-medium"
          />
        </div>
        <Button
          type="submit"
          disabled={loading}
          className="shrink-0 border-2 border-poke-black bg-poke-red font-bold text-poke-white shadow-[0_3px_0_0_var(--poke-black)] hover:bg-poke-red/90"
        >
          {loading ? "Generando…" : "Generar borrador"}
        </Button>
      </form>

      {error && (
        <p className="mt-4 rounded-xl border-2 border-poke-red bg-poke-white px-3 py-2 text-sm font-medium text-poke-red" role="alert">
          {error}
        </p>
      )}

      {data && (
        <div className="mt-8 space-y-6">
          <section>
            <h2 className="font-display text-lg font-bold text-poke-black">Equipo sugerido</h2>
            <ul className="mt-3 grid gap-3 sm:grid-cols-2">
              {data.team.map((m) => (
                <li
                  key={m.pokemon}
                  className="flex gap-3 rounded-xl border-2 border-poke-black bg-poke-white p-3 shadow-[0_3px_0_0_var(--poke-black)]"
                >
                  {m.sprite ? (
                    <img src={m.sprite} alt="" className="h-16 w-16 shrink-0 object-contain" loading="lazy" />
                  ) : (
                    <div className="h-16 w-16 shrink-0 rounded-lg skeleton" />
                  )}
                  <div className="min-w-0 flex-1">
                    <div className="font-display font-bold capitalize text-poke-black">{m.pokemon.replace(/-/g, " ")}</div>
                    <div className="mt-1 flex flex-wrap gap-1">
                      {m.types.map((t) => (
                        <TypeChip key={t} type={t} />
                      ))}
                    </div>
                    <p className="mt-1 truncate text-[11px] font-medium text-poke-black/60">
                      {m.ability.replace(/-/g, " ")}
                      {m.item ? ` · ${m.item}` : ""}
                    </p>
                  </div>
                </li>
              ))}
            </ul>
          </section>

          {topWeak.length > 0 && (
            <section>
              <h2 className="font-display text-lg font-bold text-poke-black">Debilidades frecuentes (≥2 en el equipo)</h2>
              <p className="mt-1 text-xs font-medium text-poke-black/65">Tipos que golpean fuerte a varios miembros a la vez.</p>
              <ul className="mt-2 flex flex-wrap gap-2">
                {topWeak.map(([t, n]) => (
                  <li key={t} className="inline-flex items-center gap-1 rounded-md border-2 border-poke-black bg-poke-white px-1.5 py-0.5 shadow-[0_2px_0_0_var(--poke-black)]">
                    <TypeChip type={t} />
                    <span className="font-pixel text-[9px] font-bold text-poke-black">×{n}</span>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </div>
      )}
    </div>
  );
}


