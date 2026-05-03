"use client";

import type { ConfidenceLevel } from "@/lib/types";
import { cn } from "@/lib/utils";

const LABEL: Record<ConfidenceLevel, string> = {
  verified: "✓ Verificado",
  partial: "⚠ Parcial",
  contradiction: "✗ Contradicción",
};

export function ConfidenceBadge({
  level,
  className,
}: {
  level: ConfidenceLevel;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium",
        level === "verified" && "border-emerald-500/50 bg-emerald-950/50 text-emerald-300",
        level === "partial" && "border-amber-500/50 bg-amber-950/40 text-amber-200",
        level === "contradiction" && "border-red-500/50 bg-red-950/40 text-red-200",
        className,
      )}
      title={level}
    >
      {LABEL[level]}
    </span>
  );
}
