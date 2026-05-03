import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { motion } from "framer-motion";
import { RefreshCw, AlertCircle } from "lucide-react";
import type { ChatMessage } from "@/lib/api/types";
import { ConfidenceBadge } from "@/components/pokemon/ConfidenceBadge";
import { SourcesPopover } from "@/components/pokemon/SourcesPopover";
import { DamageCard } from "@/components/pokemon/DamageCard";

function PokeballAvatar() {
  return (
    <div className="h-9 w-9 shrink-0 rounded-full border-[3px] border-poke-black bg-poke-white shadow-[0_3px_0_0_var(--poke-black)] overflow-hidden">
      <div className="h-1/2 bg-poke-red" />
      <div className="relative -mt-[1px] h-[3px] bg-poke-black" />
      <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 h-3 w-3 rounded-full bg-poke-white border-[2.5px] border-poke-black" />
    </div>
  );
}

function TrainerAvatar() {
  return (
    <div className="h-9 w-9 shrink-0 rounded-full border-[3px] border-poke-black bg-poke-yellow grid place-items-center shadow-[0_3px_0_0_var(--poke-black)]">
      <span className="font-pixel text-[10px] text-poke-black">YOU</span>
    </div>
  );
}

export function MessageBubble({ message, onRetry }: { message: ChatMessage; onRetry?: (id: string) => void }) {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} className="flex justify-end gap-3">
        <div className="relative max-w-[min(92%,42rem)] rounded-2xl rounded-tr-sm bg-poke-blue text-poke-white px-4 py-2.5 text-sm border-[3px] border-poke-black shadow-[0_3px_0_0_var(--poke-black)] font-medium">
          <p className="whitespace-pre-wrap break-words [overflow-wrap:anywhere]">{message.content}</p>
        </div>
        <TrainerAvatar />
      </motion.div>
    );
  }

  return (
    <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} className="flex gap-3">
      <PokeballAvatar />
      <div className="flex-1 min-w-0 space-y-3">
        {(message.intent || message.agent) && (
          <div className="flex flex-wrap items-center gap-1.5">
            {message.intent && <span className="font-pixel text-[8px] rounded-md bg-poke-yellow text-poke-black px-2 py-1 border-2 border-poke-black shadow-[0_2px_0_0_var(--poke-black)]">INTENT · {message.intent.toUpperCase()}</span>}
            {message.agent && <span className="font-pixel text-[8px] rounded-md bg-poke-blue text-poke-white px-2 py-1 border-2 border-poke-black shadow-[0_2px_0_0_var(--poke-black)]">AGENT · {message.agent.toUpperCase()}</span>}
          </div>
        )}

        {message.damage && <DamageCard damage={message.damage} />}

        <div className="poke-panel-soft max-w-full px-4 py-3 text-sm">
          <div className="markdown-body text-poke-black break-words [overflow-wrap:anywhere]">
            {message.content
              ? <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
              : message.streaming && <ThinkingDots />}
          </div>
          {message.error && (
            <div className="mt-3 flex items-start gap-2 rounded-lg border-2 border-poke-red bg-poke-red/10 p-2.5 text-xs text-poke-red-dark">
              <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
              <div className="flex-1"><div className="font-bold">Falló la transmisión</div><div className="opacity-90">{message.error}</div></div>
              {onRetry && (
                <button onClick={() => onRetry(message.id)} className="rounded-full bg-poke-red text-poke-white px-2.5 py-1 inline-flex items-center gap-1 border-2 border-poke-black font-bold hover:opacity-90">
                  <RefreshCw className="h-3 w-3" />Reintentar
                </button>
              )}
            </div>
          )}
        </div>

        {(message.confidence || message.sources?.length) && (
          <div className="flex items-center gap-2 flex-wrap pl-1">
            {message.confidence && <ConfidenceBadge confidence={message.confidence} />}
            {message.sources?.length ? <SourcesPopover sources={message.sources} /> : null}
          </div>
        )}
      </div>
    </motion.div>
  );
}

function ThinkingDots() {
  return (
    <span className="inline-flex items-center gap-1.5 text-poke-black/60">
      <span className="h-2 w-2 rounded-full bg-poke-red typing-dot border border-poke-black" style={{ animationDelay: "0ms" }} />
      <span className="h-2 w-2 rounded-full bg-poke-yellow typing-dot border border-poke-black" style={{ animationDelay: "180ms" }} />
      <span className="h-2 w-2 rounded-full bg-poke-blue typing-dot border border-poke-black" style={{ animationDelay: "360ms" }} />
    </span>
  );
}
