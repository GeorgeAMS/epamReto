// Cliente API único. Toda llamada al backend pasa por aquí.
// Cambia VITE_API_URL en .env (sin tocar componentes) para apuntar a otro host.
import type { ChatSource, Confidence, Pokemon, PokemonType, StreamEvent } from "./types";

export const API_BASE = (import.meta.env.VITE_API_URL ?? "http://127.0.0.1:18001").replace(/\/$/, "");

/** sessionStorage: último `conversation_id` del chat (para reportes / continuidad). */
export const LAST_CHAT_CONVERSATION_STORAGE_KEY = "pokeArca:lastConversationId";

export class ApiError extends Error {
  constructor(message: string, public status?: number, public body?: unknown) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const url = `${API_BASE}${path}`;
  let res: Response;
  try {
    res = await fetch(url, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(init.headers ?? {}),
      },
    });
  } catch (e) {
    throw new ApiError(`Network error contacting backend (${API_BASE}). Check that the FastAPI server is reachable.`);
  }
  const text = await res.text();
  const body = text ? safeJson(text) : null;
  if (!res.ok) throw new ApiError((body as any)?.detail ?? `Request failed: ${res.status}`, res.status, body);
  return body as T;
}

function safeJson(t: string): unknown { try { return JSON.parse(t); } catch { return t; } }

export const api = {
  health: () => request<{ status: string }>("/health"),

  // Pokédex
  pokedexTypes: () => request<{ types: PokemonType[] } | PokemonType[]>("/pokedex/types"),
  pokedexGenerations: () => request<{ generations: number[] } | number[]>("/pokedex/generations"),
  pokedexList: (params: { type?: string; generation?: number | string; search?: string; limit?: number; offset?: number } = {}) => {
    const qs = new URLSearchParams();
    if (params.type) qs.set("type", params.type);
    if (params.generation) qs.set("generation", String(params.generation));
    if (params.search) qs.set("search", params.search);
    if (params.limit) qs.set("limit", String(params.limit));
    if (params.offset) qs.set("offset", String(params.offset));
    const q = qs.toString();
    return request<any>(`/pokedex/pokemon${q ? `?${q}` : ""}`);
  },

  pokemonDetail: (id: number) => request<any>(`/pokedex/pokemon/${id}`),

  chat: (payload: { query: string; conversation_id?: string; context?: Record<string, unknown> }) =>
    request<any>("/chat", { method: "POST", body: JSON.stringify(payload) }),

  buildTeam: (payload: { anchor_pokemon: string; format?: string; team_size?: number }) =>
    request<any>("/teams/build", {
      method: "POST",
      body: JSON.stringify({ format: "OU", team_size: 6, ...payload }),
    }),

  conversations: () => request<any>("/conversations"),
  deleteConversation: (id: string) => request<any>(`/conversations/${id}`, { method: "DELETE" }),
  traces: (id: string) => request<any>(`/traces/${id}`),

  /** Body: JSON array de slugs PokéAPI, p. ej. `["charizard","blastoise"]`. Máx. 4. */
  comparePokemon: (pokemonNames: string[]) =>
    request<any>("/compare/", { method: "POST", body: JSON.stringify(pokemonNames) }),
};

/**
 * Streaming chat: el backend usa sse-starlette (`event:` + `data:` por frame, separados por línea en blanco).
 * También aceptamos NDJSON suelto o JSON con campo `type` por compatibilidad.
 */
export async function streamChat(
  payload: { query: string; conversation_id?: string; context?: Record<string, unknown> },
  onEvent: (ev: StreamEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(`${API_BASE}/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify(payload),
    signal,
  });
  if (!res.ok || !res.body) {
    const errText = await res.text().catch(() => "");
    throw new ApiError(`Stream failed: ${res.status} ${errText}`, res.status);
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });

    let boundary: RegExpExecArray | null;
    const re = /\r\n\r\n|\n\n/g;
    re.lastIndex = 0;
    let start = 0;
    while ((boundary = re.exec(buf)) !== null) {
      const frame = buf.slice(start, boundary.index).trim();
      start = boundary.index + boundary[0].length;
      if (frame.startsWith(":")) continue;
      const ev = parseStreamFrame(frame);
      if (ev) onEvent(ev);
    }
    buf = buf.slice(start);
  }
  const tail = buf.trim();
  if (tail && !tail.startsWith(":")) {
    const ev = parseStreamFrame(tail);
    if (ev) onEvent(ev);
  }
}

/** Interpreta un frame SSE completo o una línea NDJSON. */
function parseStreamFrame(frame: string): StreamEvent | null {
  const lines = frame.split(/\r?\n/).filter((l) => l.length > 0);
  if (lines.length && lines.every((l) => l.startsWith(":"))) return null;
  const sse = parseSseStarletteFrame(frame);
  if (sse) return sse;
  return parseChunkNdjson(frame);
}

function parseSseStarletteFrame(block: string): StreamEvent | null {
  const lines = block.split(/\r?\n/).filter((l) => l.length > 0);
  let sseEvent: string | undefined;
  const dataLines: string[] = [];
  for (const line of lines) {
    if (line.startsWith("event:")) sseEvent = line.slice(6).trim();
    else if (line.startsWith("data:")) dataLines.push(line.slice(5).trimStart());
  }
  if (!sseEvent && !dataLines.length) return null;
  const dataPayload = dataLines.join("\n");

  if (sseEvent === "token") {
    if (dataPayload === "" || dataPayload === "[DONE]") return { type: "done" };
    return { type: "token", token: dataPayload };
  }
  if (sseEvent === "intent" && dataPayload) {
    try {
      const j = JSON.parse(dataPayload) as { intent?: string };
      return { type: "intent", intent: j.intent };
    } catch {
      return { type: "intent" };
    }
  }
  if (sseEvent === "agent" && dataPayload) {
    try {
      const j = JSON.parse(dataPayload) as { agent?: string; sources?: ChatSource[] };
      return { type: "agent", agent: j.agent, sources: j.sources };
    } catch {
      return { type: "agent" };
    }
  }
  if (sseEvent === "done") {
    if (!dataPayload) return { type: "done" };
    try {
      const j = JSON.parse(dataPayload) as {
        sources?: ChatSource[];
        confidence_level?: string;
        data?: Record<string, unknown>;
      };
      const conf = j.confidence_level as Confidence | undefined;
      return {
        type: "done",
        sources: j.sources,
        confidence: conf,
        data: j.data,
      };
    } catch {
      return { type: "done" };
    }
  }

  if (sseEvent && dataPayload) {
    try {
      const obj = JSON.parse(dataPayload) as Record<string, unknown>;
      if (typeof obj.type === "string") return obj as StreamEvent;
    } catch {
      /* fall through */
    }
  }
  return null;
}

function parseChunkNdjson(chunk: string): StreamEvent | null {
  const dataLines = chunk.split(/\r?\n/).filter((l) => l.startsWith("data:"));
  const raw = dataLines.length ? dataLines.map((l) => l.replace(/^data:\s?/, "")).join("\n") : chunk;
  if (!raw || raw === "[DONE]") return { type: "done" };
  try {
    const obj = JSON.parse(raw) as Record<string, unknown>;
    if (typeof obj.type === "string") return obj as StreamEvent;
    if (typeof obj.event === "string") {
      const inner =
        typeof obj.data === "string" ? obj.data : obj.data !== undefined ? JSON.stringify(obj.data) : "";
      return parseSseStarletteFrame(`event: ${obj.event}\ndata: ${inner}`);
    }
    if (typeof obj === "string") return { type: "token", token: obj };
  } catch {
    /* plain text */
  }
  return { type: "token", token: raw };
}

// Helpers de normalización
export function normalizePokemonList(resp: any): Pokemon[] {
  if (!resp) return [];
  if (Array.isArray(resp)) return resp as Pokemon[];
  return (resp.pokemon ?? resp.results ?? resp.items ?? []) as Pokemon[];
}
export function normalizeStringList(resp: any, key: string): string[] {
  if (Array.isArray(resp)) return resp.map(String);
  if (resp && Array.isArray(resp[key])) return resp[key].map(String);
  return [];
}

/** `/pokedex/generations` devuelve `{ generations: [{ id, name, range }] }` — no usar `.map(String)` en objetos. */
export type GenerationOption = { id: string; label: string };

export function normalizeGenerationList(resp: unknown): GenerationOption[] {
  if (!resp || typeof resp !== "object") return [];
  const raw = Array.isArray(resp)
    ? resp
    : Array.isArray((resp as { generations?: unknown }).generations)
      ? (resp as { generations: unknown[] }).generations
      : [];
  const out: GenerationOption[] = [];
  for (const g of raw) {
    if (typeof g === "number") out.push({ id: String(g), label: `Gen ${g}` });
    else if (g && typeof g === "object" && "id" in g) {
      const o = g as { id: number; name?: string };
      out.push({
        id: String(o.id),
        label: typeof o.name === "string" && o.name.trim() ? o.name.trim() : `Gen ${o.id}`,
      });
    }
  }
  return out;
}
