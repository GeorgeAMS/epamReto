import { Send, Square } from "lucide-react";
import { useEffect, useRef, useState } from "react";

export function Composer({ onSend, onStop, streaming, suggestions, onPick }: {
  onSend: (text: string) => void; onStop: () => void; streaming: boolean;
  suggestions?: string[]; onPick?: (text: string) => void;
}) {
  const [value, setValue] = useState("");
  const ref = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (!ref.current) return;
    ref.current.style.height = "auto";
    ref.current.style.height = Math.min(ref.current.scrollHeight, 320) + "px";
  }, [value]);

  function submit() {
    if (!value.trim() || streaming) return;
    onSend(value);
    setValue("");
  }

  return (
    <div className="space-y-2">
      {suggestions?.length ? (
        <div className="flex gap-2 overflow-x-auto scrollbar-thin pb-1">
          {suggestions.map((s) => (
            <button
              key={s}
              onClick={() => onPick?.(s)}
              className="shrink-0 rounded-full bg-poke-white border-2 border-poke-black px-3 py-1.5 text-xs font-bold text-poke-black hover:bg-poke-yellow shadow-[0_2px_0_0_var(--poke-black)] transition-colors"
            >{s}</button>
          ))}
        </div>
      ) : null}

      <div className="relative rounded-2xl bg-poke-white border-[3px] border-poke-black shadow-[0_4px_0_0_var(--poke-black)] focus-within:bg-poke-cream transition-colors">
        <textarea
          ref={ref}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submit(); } }}
          placeholder="¿Qué quieres saber, entrenador?"
          rows={1}
          className="w-full resize-none bg-transparent px-4 py-3 pr-14 text-sm font-medium placeholder:text-poke-black/50 focus:outline-none scrollbar-thin"
        />
        <button
          onClick={streaming ? onStop : submit}
          disabled={!streaming && !value.trim()}
          className="absolute right-2 bottom-2 grid place-items-center h-10 w-10 rounded-full bg-poke-red text-poke-white border-[3px] border-poke-black shadow-[0_3px_0_0_var(--poke-black)] disabled:opacity-50 disabled:cursor-not-allowed hover:bg-poke-red-dark active:translate-y-0.5 active:shadow-[0_1px_0_0_var(--poke-black)] transition-all"
          aria-label={streaming ? "Detener" : "Enviar"}
        >
          {streaming ? <Square className="h-4 w-4" strokeWidth={3} /> : <Send className="h-4 w-4" strokeWidth={2.5} />}
        </button>
      </div>
    </div>
  );
}
