"use client";

import * as React from "react";
import { Loader2, SendHorizonal } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { DamageVisualizer } from "@/components/DamageVisualizer";
import { CitationPopover } from "@/components/CitationPopover";
import { ConfidenceBadge } from "@/components/ConfidenceBadge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import type { Source, UiMessage } from "@/lib/types";
import { cn } from "@/lib/utils";

function renderWithCitations(content: string, sources: Source[] | undefined) {
  const parts = content.split(/(\[\d+\])/g);
  return parts.map((part, i) => {
    const idxMatch = part.match(/^\[(\d+)\]$/);
    if (idxMatch) {
      const idx = parseInt(idxMatch[1], 10);
      const src = sources?.[idx - 1];
      return (
        <CitationPopover key={i} index={idx} source={src}>
          {part}
        </CitationPopover>
      );
    }
    if (!part) return null;
    return (
      <ReactMarkdown key={i} remarkPlugins={[remarkGfm]} className="inline">
        {part}
      </ReactMarkdown>
    );
  });
}

function MessageBubble({ m }: { m: UiMessage }) {
  const isUser = m.role === "user";
  return (
    <div
      className={cn(
        "flex w-full",
        isUser ? "justify-end" : "justify-start",
      )}
    >
      <Card
        className={cn(
          "max-w-[92%] border",
          isUser ? "border-arcana-ball/40 bg-arcana-ball/10" : "border-arcana-border bg-arcana-surface/90",
        )}
      >
        <CardContent className="space-y-2 p-3 text-sm">
          {!isUser && m.confidence_level ? (
            <ConfidenceBadge level={m.confidence_level} className="mb-1" />
          ) : null}
          <div
            className={cn(
              "arcana-markdown max-w-none text-sm leading-relaxed",
              isUser && "text-zinc-100",
            )}
          >
            {m.streaming && !m.content ? (
              <span className="inline-flex items-center gap-2 text-arcana-muted">
                <Loader2 className="h-4 w-4 animate-spin" /> Generando…
              </span>
            ) : (
              renderWithCitations(m.content, m.sources)
            )}
          </div>
          {!isUser && m.content ? <DamageVisualizer text={m.content} /> : null}
        </CardContent>
      </Card>
    </div>
  );
}

type ChatProps = {
  messages: UiMessage[];
  onSend: (text: string) => void;
  busy: boolean;
};

export function Chat({ messages, onSend, busy }: ChatProps) {
  const [draft, setDraft] = React.useState("");

  const submit = () => {
    const t = draft.trim();
    if (!t || busy) return;
    setDraft("");
    onSend(t);
  };

  return (
    <Card className="flex min-h-0 flex-1 flex-col border-arcana-border/80">
      <CardContent className="flex min-h-0 flex-1 flex-col gap-3 p-4">
        <div className="min-h-[280px] flex-1 space-y-3 overflow-y-auto pr-1 sm:min-h-[360px]">
          {messages.map((m) => (
            <MessageBubble key={m.id} m={m} />
          ))}
        </div>
        <div className="flex gap-2 border-t border-arcana-border/60 pt-3">
          <textarea
            className="min-h-[44px] flex-1 resize-y rounded-md border border-arcana-border bg-arcana-bg px-3 py-2 text-sm text-zinc-100 placeholder:text-arcana-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-arcana-ball"
            rows={2}
            placeholder="Pregunta algo sobre Pokémon…"
            value={draft}
            disabled={busy}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                submit();
              }
            }}
          />
          <Button
            type="button"
            variant="gold"
            className="shrink-0 self-end"
            disabled={busy}
            onClick={submit}
          >
            {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <SendHorizonal className="h-4 w-4" />}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
