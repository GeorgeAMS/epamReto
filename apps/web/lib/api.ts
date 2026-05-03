import type {
  ChatResponse,
  ConfidenceLevel,
  ReportResponse,
  Source,
  StreamEvent,
  TraceDTO,
} from "./types";

export function getApiBase(): string {
  const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:18000";
  return API_BASE_URL.replace(/\/$/, "");
}

export async function createConversation(): Promise<{ id: string }> {
  const r = await fetch(`${getApiBase()}/conversations`, { method: "POST" });
  if (!r.ok) throw new Error(`createConversation: ${r.status}`);
  return r.json();
}

export async function postChat(body: {
  query: string;
  conversation_id?: string | null;
  context?: Record<string, unknown> | null;
}): Promise<ChatResponse> {
  const r = await fetch(`${getApiBase()}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query: body.query,
      conversation_id: body.conversation_id ?? null,
      context: body.context ?? null,
    }),
  });
  if (!r.ok) throw new Error(`postChat: ${r.status}`);
  return r.json();
}

export async function fetchTrace(conversationId: string): Promise<TraceDTO> {
  const r = await fetch(`${getApiBase()}/traces/${conversationId}`);
  if (!r.ok) throw new Error(`fetchTrace: ${r.status}`);
  return r.json();
}

export async function postReport(body: {
  query?: string | null;
  conversation_id?: string | null;
  context?: Record<string, unknown> | null;
}): Promise<ReportResponse> {
  const r = await fetch(`${getApiBase()}/reports/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`postReport: ${r.status} ${await r.text()}`);
  return r.json();
}

/** Descarga /reports/file — la API valida que path caiga bajo reports_dir. */
export function reportFileUrl(path: string): string {
  const enc = encodeURIComponent(path);
  return `${getApiBase()}/reports/file?path=${enc}`;
}

/** POST /chat/stream — parseo manual SSE (EventSource no soporta POST). */
export async function streamChat(
  body: {
    query: string;
    conversation_id?: string | null;
    context?: Record<string, unknown> | null;
  },
  onEvent: (ev: StreamEvent) => void,
  opts?: { signal?: AbortSignal },
): Promise<void> {
  const r = await fetch(`${getApiBase()}/chat/stream`, {
    method: "POST",
    headers: {
      Accept: "text/event-stream",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      query: body.query,
      conversation_id: body.conversation_id ?? null,
      context: body.context ?? null,
    }),
    signal: opts?.signal,
  });

  if (!r.ok || !r.body) throw new Error(`streamChat: ${r.status}`);

  const reader = r.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  const flushBlock = (block: string) => {
    let eventName = "message";
    const dataLines: string[] = [];
    for (const line of block.split(/\r\n|\n/)) {
      if (line.startsWith("event:")) eventName = line.slice(6).trim();
      else if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
    }
    const dataStr = dataLines.join("\n");
    if (!dataStr) return;

    if (eventName === "intent") {
      try {
        const payload = JSON.parse(dataStr) as {
          intent?: string;
          entities?: Record<string, unknown>;
        };
        onEvent({ type: "intent", payload });
      } catch {
        onEvent({ type: "intent", payload: {} });
      }
      return;
    }

    if (eventName === "agent") {
      const payload = JSON.parse(dataStr) as {
        agent: string;
        confidence: number;
        sources: Source[];
      };
      onEvent({ type: "agent", payload });
      return;
    }

    if (eventName === "token") {
      onEvent({ type: "token", payload: dataStr });
      return;
    }

    if (eventName === "done") {
      const raw = JSON.parse(dataStr) as {
        trace_id: string;
        confidence: number;
        confidence_level: string;
        sources: Source[];
        data: Record<string, unknown>;
      };
      onEvent({
        type: "done",
        payload: {
          trace_id: raw.trace_id,
          confidence: raw.confidence,
          confidence_level: raw.confidence_level as ConfidenceLevel,
          sources: raw.sources ?? [],
          data: raw.data ?? {},
        },
      });
    }
  };

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split(/\r\n\r\n|\n\n/);
    buffer = parts.pop() ?? "";
    for (const part of parts) {
      if (part.trim()) flushBlock(part);
    }
  }
  if (buffer.trim()) flushBlock(buffer);
}
