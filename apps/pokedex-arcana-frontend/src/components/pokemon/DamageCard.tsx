import type { DamageData } from "@/lib/api/types";
import { Swords, Zap, Cloud, Target } from "lucide-react";
import { motion } from "framer-motion";

function effLabel(eff?: number) {
  if (eff == null) return null;
  if (eff === 0) return { txt: "Inmune", cls: "bg-poke-black text-poke-white" };
  if (eff >= 4) return { txt: "4× Súper efectivo", cls: "bg-emerald-500 text-poke-white" };
  if (eff >= 2) return { txt: "2× Súper efectivo", cls: "bg-emerald-400 text-poke-black" };
  if (eff >= 1) return { txt: "1× Neutro", cls: "bg-poke-white text-poke-black" };
  if (eff >= 0.5) return { txt: "0.5× Poco efectivo", cls: "bg-poke-yellow text-poke-black" };
  return { txt: "0.25× Muy poco", cls: "bg-poke-red text-poke-white" };
}

export function DamageCard({ damage }: { damage: DamageData }) {
  const range = damage.damage_range;
  const pct = damage.percent_range ?? (damage.percent != null ? [damage.percent, damage.percent] as [number, number] : undefined);
  const eff = effLabel(damage.type_effectiveness);
  const minPct = pct?.[0] ?? 0;
  const maxPct = pct?.[1] ?? 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      className="relative overflow-hidden rounded-2xl border-[3px] border-poke-black bg-poke-white shadow-[0_5px_0_0_var(--poke-black)]"
    >
      {/* Header rojo Pokédex */}
      <div className="bg-poke-red px-4 py-2 border-b-[3px] border-poke-black flex items-center gap-2">
        <div className="h-5 w-5 rounded-full bg-poke-blue border-2 border-poke-black ring-2 ring-poke-white" />
        <div className="flex-1">
          <div className="font-pixel text-[8px] text-poke-white/90 leading-none">CALCULO DETERMINISTA</div>
          <div className="font-display text-sm font-bold text-poke-white leading-tight mt-0.5 truncate">
            {damage.attacker ?? "Atacante"} <span className="opacity-80">VS</span> {damage.defender ?? "Defensor"}
          </div>
        </div>
        <Swords className="h-5 w-5 text-poke-white" strokeWidth={2.5} />
      </div>

      <div className="p-4">
        {damage.move && (
          <div className="mb-4 inline-flex items-center gap-1.5 rounded-full bg-poke-yellow border-2 border-poke-black px-3 py-1 text-xs shadow-[0_2px_0_0_var(--poke-black)]">
            <Zap className="h-3 w-3 text-poke-black" strokeWidth={3} fill="currentColor" />
            <span className="font-bold uppercase text-poke-black">{damage.move}</span>
            {damage.is_stab && <span className="ml-1 font-pixel text-[8px] text-poke-red">STAB</span>}
            {damage.is_critical && <span className="ml-1 font-pixel text-[8px] text-poke-red">CRIT!</span>}
          </div>
        )}

        <div className="grid grid-cols-2 gap-3 mb-4">
          <Stat label="DAÑO" value={range ? `${range[0]}–${range[1]}` : damage.damage?.toString() ?? "—"} />
          <Stat label="% HP" value={pct ? (minPct === maxPct ? `${minPct.toFixed(1)}%` : `${minPct.toFixed(1)}–${maxPct.toFixed(1)}%`) : "—"} highlight />
        </div>

        {pct && (
          <div className="mb-4">
            <div className="font-pixel text-[8px] text-poke-black/70 mb-1">HP DEL DEFENSOR</div>
            <div className="h-4 rounded-full bg-poke-black p-[2px] border-2 border-poke-black overflow-hidden">
              <div className="h-full rounded-full bg-poke-cream relative overflow-hidden">
                <div
                  className="absolute inset-y-0 left-0 bg-gradient-to-r from-emerald-400 via-poke-yellow to-poke-red rounded-full"
                  style={{ width: `${Math.min(100, maxPct)}%` }}
                />
                {minPct !== maxPct && (
                  <div className="absolute inset-y-0 left-0 border-r-[2px] border-poke-black" style={{ width: `${Math.min(100, minPct)}%` }} />
                )}
              </div>
            </div>
            <div className="mt-1 font-pixel text-[8px] text-poke-black/60 flex justify-between">
              <span>0%</span><span>50%</span><span>KO 100%</span>
            </div>
          </div>
        )}

        <div className="flex flex-wrap items-center gap-2">
          {eff && <span className={`inline-flex items-center gap-1 rounded-full border-2 border-poke-black px-2.5 py-0.5 font-pixel text-[9px] uppercase shadow-[0_2px_0_0_var(--poke-black)] ${eff.cls}`}><Target className="h-3 w-3" strokeWidth={3} />{eff.txt}</span>}
          {damage.weather && <span className="inline-flex items-center gap-1 rounded-full border-2 border-poke-black bg-poke-blue text-poke-white px-2.5 py-0.5 font-pixel text-[9px] uppercase shadow-[0_2px_0_0_var(--poke-black)]"><Cloud className="h-3 w-3" strokeWidth={3} />{damage.weather}</span>}
        </div>

        {damage.notes && <p className="mt-3 text-xs text-poke-black/70 italic">{damage.notes}</p>}
      </div>
    </motion.div>
  );
}

function Stat({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div className={`rounded-xl border-2 border-poke-black px-3 py-2 ${highlight ? "bg-poke-yellow" : "bg-poke-cream"} shadow-[0_2px_0_0_var(--poke-black)]`}>
      <div className="font-pixel text-[8px] text-poke-black/70">{label}</div>
      <div className="font-display text-2xl font-bold text-poke-black tabular-nums">{value}</div>
    </div>
  );
}
