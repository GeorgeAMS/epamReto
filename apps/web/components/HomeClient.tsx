"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { GitBranch, FileDown, Sparkles } from "lucide-react";
import { AgentGraphModal } from "@/components/AgentGraphModal";
import { AgentTracePanel } from "@/components/AgentTracePanel";
import { Chat } from "@/components/Chat";
import { TeamBuilder } from "@/components/TeamBuilder";
import { Button } from "@/components/ui/button";
import {
  createConversation,
  fetchTrace,
  getApiBase,
  postReport,
  reportFileUrl,
  streamChat,
} from "@/lib/api";
import type { TimelineEventDTO, UiMessage } from "@/lib/types";

function newId(): string {
  if (typeof crypto !== "undefined" && crypto.randomUUID) return crypto.randomUUID();
  return Math.random().toString(36).slice(2);
}

export function HomeClient() {
  const router = useRouter();
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [initError, setInitError] = useState<string | null>(null);
  const [messages, setMessages] = useState<UiMessage[]>([]);
  const [timeline, setTimeline] = useState<TimelineEventDTO[]>([]);
  const [activeHint, setActiveHint] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [graphOpen, setGraphOpen] = useState(false);
  const [reportErr, setReportErr] = useState<string | null>(null);
  const [lastIntent, setLastIntent] = useState<string | null>(null);
  const [lastQuery, setLastQuery] = useState<string>("");
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    let cancelled = false;
    createConversation()
      .then((c) => {
        if (!cancelled) setConversationId(c.id);
      })
      .catch(() => {
        if (!cancelled) setInitError("No se pudo crear conversación — ¿API en :8000?");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const refreshTrace = useCallback(async (cid: string) => {
    try {
      const t = await fetchTrace(cid);
      setTimeline(t.timeline);
    } catch {
      /* timeline opcional */
    }
  }, []);

  const onSend = async (text: string) => {
    if (!conversationId) return;
    setLastQuery(text);
    const userMsg: UiMessage = { id: newId(), role: "user", content: text };
    const asstId = newId();
    setMessages((prev) => [
      ...prev,
      userMsg,
      { id: asstId, role: "assistant", content: "", streaming: true },
    ]);
    setActiveHint("Clasificando…");
    abortRef.current?.abort();
    abortRef.current = new AbortController();
    setBusy(true);
    try {
      await streamChat(
        { query: text, conversation_id: conversationId },
        (ev) => {
          if (ev.type === "intent")
            setActiveHint(`Intent · ${ev.payload.intent ?? "?"}`);
          if (ev.type === "intent") setLastIntent(ev.payload.intent ?? null);
          if (ev.type === "agent")
            setActiveHint(`Consultando · ${ev.payload.agent} (${ev.payload.confidence.toFixed(2)})`);
          if (ev.type === "token") {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === asstId ? { ...m, content: m.content + ev.payload } : m,
              ),
            );
          }
          if (ev.type === "done") {
            setActiveHint("Verificando / sintetizando…");
            setMessages((prev) =>
              prev.map((m) =>
                m.id === asstId
                  ? {
                      ...m,
                      streaming: false,
                      sources: ev.payload.sources,
                      confidence_level: ev.payload.confidence_level,
                    }
                  : m,
              ),
            );
            setActiveHint(null);
            if (typeof ev.payload.data.intent === "string") {
              setLastIntent(ev.payload.data.intent);
            }
          }
        },
        { signal: abortRef.current.signal },
      );
      await refreshTrace(conversationId);
    } catch (e) {
      if ((e as Error).name === "AbortError") return;
      setMessages((prev) =>
        prev.map((m) =>
          m.id === asstId
            ? {
                ...m,
                streaming: false,
                content: `Error de red o API: ${(e as Error).message}`,
                confidence_level: "contradiction",
              }
            : m,
        ),
      );
    } finally {
      setBusy(false);
    }
  };

  const onReport = async () => {
    if (!conversationId) return;
    setReportErr(null);
    try {
      const rep = await postReport({ conversation_id: conversationId });
      const path = rep.pdf_path ?? rep.md_path;
      window.open(reportFileUrl(path), "_blank", "noopener,noreferrer");
    } catch (e) {
      setReportErr((e as Error).message);
    }
  };

  return (
    <>
      <div className="min-h-screen bg-arcana-bg">
        <header className="flex flex-wrap items-center justify-between gap-3 border-b border-arcana-border px-4 py-3">
          <div className="flex items-center gap-2">
            <Sparkles className="h-7 w-7 text-arcana-gold" />
            <div>
              <h1 className="font-semibold tracking-tight text-arcana-gold">Pokédex Arcana</h1>
              <p className="font-mono text-[10px] text-arcana-muted">API · {getApiBase()}</p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="gap-1"
              onClick={() => setGraphOpen(true)}
            >
              <GitBranch className="h-3.5 w-3.5" /> Ver grafo
            </Button>
            <Button
              type="button"
              variant="gold"
              size="sm"
              className="gap-1"
              disabled={!conversationId || busy}
              onClick={onReport}
            >
              <FileDown className="h-3.5 w-3.5" /> Generate Report
            </Button>
          </div>
        </header>

        {initError ? (
          <p className="p-4 text-center text-red-300">{initError}</p>
        ) : null}
        {reportErr ? (
          <p className="p-2 text-center text-amber-300">{reportErr}</p>
        ) : null}

        <div className="mx-auto grid max-w-[1700px] gap-4 p-4 lg:grid-cols-[1fr_380px]">
          <main className="flex min-h-0 flex-col gap-4">
            {!conversationId ? (
              <p className="text-center text-arcana-muted">Inicializando conversación…</p>
            ) : (
              <Chat messages={messages} onSend={onSend} busy={busy || !conversationId} />
            )}
            {lastIntent === "strategy" && (
              <Button
                variant="outline"
                onClick={() => router.push(`/teams/builder?anchor=${encodeURIComponent(lastQuery.split(/\s+/)[0] ?? "")}`)}
              >
                Open in Team Builder
              </Button>
            )}
            <TeamBuilder />
          </main>
          <aside className="flex min-h-0 flex-col gap-3">
            <AgentTracePanel timeline={timeline} activeHint={activeHint} />
          </aside>
        </div>
      </div>
      <AgentGraphModal open={graphOpen} onOpenChange={setGraphOpen} />
    </>
  );
}
