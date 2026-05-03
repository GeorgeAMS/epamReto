import { motion, AnimatePresence } from "framer-motion";

export function PipelineIndicator({ pipeline, streaming }: { pipeline: { intent?: string; agent?: string; status: string }; streaming: boolean }) {
  const visible = streaming || pipeline.status === "thinking" || pipeline.status === "running";
  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.9 }}
          className="flex items-center gap-2 rounded-full bg-poke-white border-2 border-poke-black px-3 py-1 shadow-[0_2px_0_0_var(--poke-black)]"
        >
          <svg viewBox="0 0 24 24" className="h-4 w-4 pokeball-shake" aria-hidden="true">
            <circle cx="12" cy="12" r="10" fill="#fff" stroke="#1a1a1a" strokeWidth="2" />
            <path d="M2 12 a10 10 0 0 1 20 0 z" fill="var(--poke-red)" stroke="#1a1a1a" strokeWidth="2" />
            <line x1="2" y1="12" x2="22" y2="12" stroke="#1a1a1a" strokeWidth="2" />
            <circle cx="12" cy="12" r="3" fill="#fff" stroke="#1a1a1a" strokeWidth="2" />
          </svg>
          <span className="font-pixel text-[9px] text-poke-black">
            {pipeline.status === "thinking" ? "BUSCANDO…" : "PROCESANDO"}
            {pipeline.intent && <span className="text-poke-red"> · {pipeline.intent.toUpperCase()}</span>}
            {pipeline.agent && <span className="text-poke-blue"> · {pipeline.agent.toUpperCase()}</span>}
          </span>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
