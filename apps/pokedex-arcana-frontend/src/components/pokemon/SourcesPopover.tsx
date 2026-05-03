import type { ChatSource } from "@/lib/api/types";
import { ExternalLink, BookOpen } from "lucide-react";
import { useState } from "react";

export function SourcesPopover({ sources }: { sources: ChatSource[] }) {
  const [open, setOpen] = useState(false);
  if (!sources?.length) return null;
  return (
    <div className="relative">
      <button
        onClick={() => setOpen((v) => !v)}
        className="inline-flex items-center gap-1.5 rounded-full bg-poke-white border-2 border-poke-black px-2.5 py-0.5 font-pixel text-[8px] uppercase tracking-wider hover:bg-poke-yellow transition-colors shadow-[0_2px_0_0_var(--poke-black)]"
      >
        <BookOpen className="h-3 w-3 text-poke-blue" strokeWidth={3} />
        {sources.length} FUENTE{sources.length > 1 ? "S" : ""}
      </button>
      {open && (
        <div className="absolute z-20 mt-2 w-80 max-h-72 overflow-auto scrollbar-thin poke-panel-soft p-2 left-0 sm:right-auto">
          {sources.map((s, i) => (
            <a
              key={i}
              href={s.url}
              target="_blank"
              rel="noreferrer noopener"
              className="block rounded-lg px-3 py-2 hover:bg-poke-cream transition-colors"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="text-xs font-bold text-poke-black line-clamp-1">{s.title ?? s.source ?? s.url}</div>
                {s.url && <ExternalLink className="h-3 w-3 text-poke-blue shrink-0 mt-0.5" />}
              </div>
              {s.snippet && <p className="text-[11px] text-poke-black/70 line-clamp-2 mt-0.5">{s.snippet}</p>}
            </a>
          ))}
        </div>
      )}
    </div>
  );
}
