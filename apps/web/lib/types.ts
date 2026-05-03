/** Contractos alineados con Pydantic en la API Python. */

export type ConfidenceLevel = "verified" | "partial" | "contradiction";

export interface Source {
  id: string;
  title: string;
  url?: string | null;
  snippet?: string | null;
  kind?: string;
}

export interface ChatResponse {
  agent: string;
  content: string;
  confidence: number;
  confidence_level: ConfidenceLevel;
  sources: Source[];
  data: Record<string, unknown>;
  trace_id: string;
  conversation_id: string;
}

export interface TraceTurnDTO {
  id: string;
  role: string;
  confidence: string;
  citation_count: number;
  created_at: string;
}

export interface TimelineEventDTO {
  ts_iso: string;
  trace_id: string;
  kind: string;
  detail: Record<string, unknown>;
}

export interface TraceDTO {
  conversation_id: string;
  turn_count: number;
  turns: TraceTurnDTO[];
  langfuse_enabled: boolean;
  langfuse_url: string | null;
  timeline: TimelineEventDTO[];
}

export interface ReportResponse {
  md_path: string;
  pdf_path: string | null;
  trace_id: string;
  confidence: number;
  confidence_level: string;
  sources: Source[];
}

export type ChatRole = "user" | "assistant";

export interface UiMessage {
  id: string;
  role: ChatRole;
  content: string;
  confidence_level?: ConfidenceLevel;
  sources?: Source[];
  streaming?: boolean;
}

export type StreamEvent =
  | { type: "intent"; payload: { intent?: string; entities?: Record<string, unknown> } }
  | {
      type: "agent";
      payload: { agent: string; confidence: number; sources: Source[] };
    }
  | { type: "token"; payload: string }
  | {
      type: "done";
      payload: {
        trace_id: string;
        confidence: number;
        confidence_level: ConfidenceLevel;
        sources: Source[];
        data: Record<string, unknown>;
      };
    };
