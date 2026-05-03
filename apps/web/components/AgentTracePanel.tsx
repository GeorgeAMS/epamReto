"use client";

import { motion } from "framer-motion";
import { Brain, Calculator, Book, Shield, FileText, Sparkles } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { TimelineEventDTO } from "@/lib/types";
import { cn } from "@/lib/utils";

type AgentStatus = "thinking" | "running" | "completed" | "failed";
type AgentTrace = { agent: string; status: AgentStatus; timestamp: number; message?: string };

const AGENT_ICONS: Record<string, typeof Brain> = {
  orchestrator: Brain,
  stats_agent: FileText,
  calculator_agent: Calculator,
  lore_agent: Book,
  strategy_agent: Sparkles,
  verifier_agent: Shield,
};

const AGENT_COLORS: Record<string, string> = {
  orchestrator: "bg-purple-500",
  stats_agent: "bg-blue-500",
  calculator_agent: "bg-green-500",
  lore_agent: "bg-yellow-500",
  strategy_agent: "bg-pink-500",
  verifier_agent: "bg-red-500",
};

export function AgentTracePanel({
  timeline,
  activeHint,
}: {
  timeline: TimelineEventDTO[];
  activeHint?: string | null;
}) {
  const traces = timelineToAgentTraces(timeline, activeHint);

  return (
    <Card className="border-arcana-border/80">
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-base text-[color:var(--pokedex-yellow)]">
          <Brain className="h-4 w-4" />
          Agent Trace
        </CardTitle>
        <p className="text-xs text-arcana-muted">{activeHint || "Timeline en vivo desde SSE + API"}</p>
      </CardHeader>
      <CardContent className="max-h-[420px] space-y-3 overflow-y-auto pr-1 text-xs">
        {traces.map((trace, i) => {
          const Icon = AGENT_ICONS[trace.agent] || Brain;
          const color = AGENT_COLORS[trace.agent] || "bg-gray-500";
          return (
            <motion.div
              key={`${trace.timestamp}-${trace.agent}-${i}`}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.08 }}
              className="animate-slide-in relative flex items-start gap-3 rounded-lg border border-arcana-border/70 bg-gray-800/70 p-3"
            >
              <div className="absolute bottom-[-10px] left-5 top-[44px] w-px bg-arcana-border/60 last:hidden" />
              <div className={cn("rounded p-2", color)}>
                <Icon className="h-4 w-4 text-white" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="mb-1 flex items-center justify-between gap-2">
                  <span className="truncate text-sm font-medium text-zinc-100">{trace.agent}</span>
                  <span className="shrink-0 text-xs text-gray-400">{getRelativeTime(trace.timestamp)}</span>
                </div>
                {trace.message ? <p className="truncate text-xs text-gray-400">{trace.message}</p> : null}
                <div className="mt-2">
                  <StatusBadge status={trace.status} />
                </div>
              </div>
            </motion.div>
          );
        })}
        {traces.length === 0 ? (
          <p className="text-arcana-muted">Sin eventos aún — envía un mensaje.</p>
        ) : null}
      </CardContent>
    </Card>
  );
}

function StatusBadge({ status }: { status: AgentStatus }) {
  if (status === "thinking") {
    return <span className="agent-badge bg-yellow-500/20 text-yellow-300">Thinking...</span>;
  }
  if (status === "running") {
    return <span className="agent-badge bg-blue-500/20 text-blue-300">Running...</span>;
  }
  if (status === "failed") {
    return <span className="agent-badge bg-red-500/20 text-red-300">Failed</span>;
  }
  return <span className="agent-badge bg-green-500/20 text-green-300">Completed</span>;
}

function timelineToAgentTraces(timeline: TimelineEventDTO[], activeHint?: string | null): AgentTrace[] {
  const traces: AgentTrace[] = timeline.map((ev) => {
    const evAgent = typeof ev.detail.agent === "string" ? ev.detail.agent : undefined;
    const agent = evAgent ?? (ev.kind === "intent" ? "orchestrator" : ev.kind);
    const ts = Date.parse(ev.ts_iso);

    const status: AgentStatus =
      ev.kind === "done" || ev.kind === "chat_sync"
        ? "completed"
        : ev.kind === "error"
          ? "failed"
          : ev.kind === "token"
            ? "running"
            : "thinking";

    const message =
      typeof ev.detail.message === "string"
        ? ev.detail.message
        : ev.kind === "intent"
          ? String((ev.detail as { intent?: string }).intent ?? "intent")
          : ev.kind;
    return { agent, status, timestamp: Number.isFinite(ts) ? ts : Date.now(), message };
  });

  if (activeHint) {
    traces.unshift({
      agent: "orchestrator",
      status: "running",
      timestamp: Date.now(),
      message: activeHint,
    });
  }
  return traces;
}

function getRelativeTime(timestamp: number): string {
  const seconds = Math.max(0, Math.floor((Date.now() - timestamp) / 1000));
  if (seconds < 5) return "just now";
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  return `${hours}h ago`;
}
