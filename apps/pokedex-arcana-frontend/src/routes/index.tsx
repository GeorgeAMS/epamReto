import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useRef } from "react";
import { useChat } from "@/features/chat/useChat";
import { MessageBubble } from "@/features/chat/MessageBubble";
import { Composer } from "@/features/chat/Composer";
import { PipelineIndicator } from "@/features/chat/PipelineIndicator";
import { Trash2 } from "lucide-react";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Chat — Pokédex Arcana" },
      { name: "description", content: "Pregúntale al Profesor Arcana sobre stats, daño, lore y estrategia." },
    ],
  }),
  component: ChatPage,
});

const SUGGESTIONS = [
  "Dame stats base de Garchomp",
  "¿Cuánto daño hace Garchomp con Earthquake contra Blissey defensiva estándar?",
  "Rain-boosted Hydro from Venusaur to Charizard — recheck numbers?",
  "Recomienda equipo para Garchomp en OU",
  "Cuéntame el lore de Pikachu en Kanto",
];

function ChatPage() {
  const { messages, send, stop, retry, reset, streaming, pipeline } = useChat();
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const empty = messages.length === 0;

  return (
    <div className="mx-auto flex h-[calc(100vh-4.5rem)] min-h-0 max-w-4xl flex-col px-4">
      <div className="flex items-center justify-between py-3">
        <div className="flex items-center gap-2">
          <h1 className="font-display text-xl font-bold text-poke-black">Chat</h1>
          <PipelineIndicator pipeline={pipeline} streaming={streaming} />
        </div>
        {!empty && (
          <button
            onClick={reset}
            className="inline-flex items-center gap-1 rounded-full bg-poke-white border-2 border-poke-black text-xs font-bold text-poke-black px-3 py-1 hover:bg-poke-yellow shadow-[0_2px_0_0_var(--poke-black)]"
          >
            <Trash2 className="h-3 w-3" strokeWidth={2.5} />Nueva
          </button>
        )}
      </div>

      <div ref={scrollRef} className="min-h-0 flex-1 overflow-y-auto overflow-x-hidden scrollbar-thin py-4 space-y-5">
        {empty ? (
          <EmptyState onPick={send} />
        ) : (
          messages.map((m) => <MessageBubble key={m.id} message={m} onRetry={retry} />)
        )}
      </div>

      <div className="py-3 border-t-[3px] border-poke-black/20">
        <Composer
          onSend={send}
          onStop={stop}
          streaming={streaming}
          suggestions={empty ? undefined : SUGGESTIONS.slice(0, 3)}
          onPick={send}
        />
        <p className="mt-2 text-center font-pixel text-[8px] text-poke-black/60">ENTER ENVIA · SHIFT+ENTER NUEVA LINEA</p>
      </div>
    </div>
  );
}

function ProfessorAvatar() {
  return (
    <div className="relative h-24 w-24 mx-auto float">
      {/* Pokéball grande */}
      <svg viewBox="0 0 100 100" className="h-full w-full drop-shadow-[4px_6px_0_rgba(0,0,0,0.35)]">
        <circle cx="50" cy="50" r="46" fill="#fff" stroke="#1a1a1a" strokeWidth="6" />
        <path d="M4 50 a46 46 0 0 1 92 0 z" fill="var(--poke-red)" stroke="#1a1a1a" strokeWidth="6" />
        <line x1="4" y1="50" x2="96" y2="50" stroke="#1a1a1a" strokeWidth="6" />
        <circle cx="50" cy="50" r="13" fill="#fff" stroke="#1a1a1a" strokeWidth="6" />
        <circle cx="50" cy="50" r="5" fill="#1a1a1a" />
        {/* Brillo */}
        <ellipse cx="32" cy="28" rx="9" ry="5" fill="#fff" opacity="0.7" />
      </svg>
    </div>
  );
}

function EmptyState({ onPick }: { onPick: (t: string) => void }) {
  return (
    <div className="flex flex-col items-center justify-center text-center py-8 px-2">
      <ProfessorAvatar />
      <div className="mt-5 font-pixel text-[10px] text-poke-blue uppercase">Profesor Arcana</div>
      <h2 className="font-display text-3xl sm:text-4xl font-bold tracking-tight text-poke-black mt-2">
        ¡Hola, entrenador!
      </h2>
      <p className="mt-2 max-w-md text-sm text-poke-black/70 font-medium">
        Soy tu asistente Pokédex con cálculo de daño determinista, lore verificado y estrategia competitiva. ¿Por dónde empezamos?
      </p>

      <div className="mt-6 grid gap-2 w-full max-w-xl">
        {SUGGESTIONS.map((s, i) => (
          <button
            key={s}
            onClick={() => onPick(s)}
            className="group text-left rounded-2xl bg-poke-white border-[3px] border-poke-black px-4 py-3 text-sm font-medium text-poke-black hover:bg-poke-yellow transition-colors shadow-[0_3px_0_0_var(--poke-black)] hover:shadow-[0_5px_0_0_var(--poke-black)] hover:-translate-y-0.5 flex items-start gap-3"
          >
            <span className="font-pixel text-[9px] text-poke-red mt-1 shrink-0">{String(i + 1).padStart(2, "0")}</span>
            <span className="flex-1">{s}</span>
            <span className="text-poke-red font-bold group-hover:translate-x-1 transition-transform">›</span>
          </button>
        ))}
      </div>
    </div>
  );
}
