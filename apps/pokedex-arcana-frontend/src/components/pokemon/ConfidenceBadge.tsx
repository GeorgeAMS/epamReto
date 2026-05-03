import { CheckCircle2, AlertTriangle, XCircle, HelpCircle } from "lucide-react";
import type { Confidence } from "@/lib/api/types";

const map: Record<Confidence, { label: string; cls: string; Icon: typeof CheckCircle2 }> = {
  verified: { label: "Verificado", cls: "bg-emerald-400 text-poke-black", Icon: CheckCircle2 },
  partial: { label: "Parcial", cls: "bg-poke-yellow text-poke-black", Icon: AlertTriangle },
  contradiction: { label: "Conflicto", cls: "bg-poke-red text-poke-white", Icon: XCircle },
  unknown: { label: "Sin verificar", cls: "bg-poke-white text-poke-black", Icon: HelpCircle },
};

export function ConfidenceBadge({ confidence }: { confidence: Confidence }) {
  const m = map[confidence] ?? map.unknown;
  const Icon = m.Icon;
  return (
    <span className={`inline-flex items-center gap-1 rounded-full border-2 border-poke-black px-2.5 py-0.5 font-pixel text-[8px] uppercase tracking-wider shadow-[0_2px_0_0_var(--poke-black)] ${m.cls}`}>
      <Icon className="h-3 w-3" strokeWidth={3} />{m.label}
    </span>
  );
}
