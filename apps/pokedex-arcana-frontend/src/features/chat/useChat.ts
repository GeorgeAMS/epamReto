import { useCallback, useRef, useState } from "react";
import { streamChat, ApiError, LAST_CHAT_CONVERSATION_STORAGE_KEY } from "@/lib/api/client";
import type { ChatMessage } from "@/lib/api/types";

function uid() { return Math.random().toString(36).slice(2, 10); }

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [pipeline, setPipeline] = useState<{ intent?: string; agent?: string; status: "idle" | "thinking" | "running" | "done" }>({ status: "idle" });
  const abortRef = useRef<AbortController | null>(null);
  const conversationId = useRef<string>(uid());

  const update = useCallback((id: string, patch: Partial<ChatMessage>) => {
    setMessages((prev) => prev.map((m) => (m.id === id ? { ...m, ...patch } : m)));
  }, []);

  const send = useCallback(async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || streaming) return;

    const userMsg: ChatMessage = { id: uid(), role: "user", content: trimmed, createdAt: Date.now() };
    const aiId = uid();
    const aiMsg: ChatMessage = { id: aiId, role: "assistant", content: "", createdAt: Date.now(), streaming: true };
    setMessages((prev) => [...prev, userMsg, aiMsg]);
    setStreaming(true);
    setPipeline({ status: "thinking" });

    const ctrl = new AbortController();
    abortRef.current = ctrl;
    let acc = "";

    try {
      sessionStorage.setItem(LAST_CHAT_CONVERSATION_STORAGE_KEY, conversationId.current);
      await streamChat(
        { query: trimmed, conversation_id: conversationId.current },
        (ev) => {
          switch (ev.type) {
            case "intent":
              setPipeline((p) => ({ ...p, intent: ev.intent, status: "running" }));
              update(aiId, { intent: ev.intent });
              break;
            case "agent":
              setPipeline((p) => ({ ...p, agent: ev.agent, status: "running" }));
              update(aiId, {
                agent: ev.agent,
                ...(ev.sources?.length ? { sources: ev.sources } : {}),
              });
              break;
            case "token":
            case "delta": {
              const chunk = ev.token ?? ev.delta ?? ev.text ?? ev.content ?? "";
              if (chunk) { acc += chunk; update(aiId, { content: acc }); }
              break;
            }
            case "sources":
              if (ev.sources) update(aiId, { sources: ev.sources });
              break;
            case "confidence":
              if (ev.confidence) update(aiId, { confidence: ev.confidence });
              break;
            case "damage":
              if (ev.damage) update(aiId, { damage: ev.damage });
              break;
            case "data":
              if (ev.data) update(aiId, { data: ev.data });
              break;
            case "error":
              update(aiId, { error: ev.message ?? "Stream error" });
              break;
            case "done":
              update(aiId, {
                ...(ev.sources?.length ? { sources: ev.sources } : {}),
                ...(ev.confidence ? { confidence: ev.confidence } : {}),
                ...(ev.data ? { data: ev.data } : {}),
              });
              break;
          }
        },
        ctrl.signal,
      );
      update(aiId, { streaming: false });
      setPipeline({ status: "done" });
    } catch (e) {
      const err = e instanceof ApiError ? e.message : (e as Error)?.message ?? "Error desconocido";
      update(aiId, { streaming: false, error: err, content: acc });
      setPipeline({ status: "idle" });
    } finally {
      setStreaming(false);
      abortRef.current = null;
    }
  }, [streaming, update]);

  const stop = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setStreaming(false);
  }, []);

  const retry = useCallback((id: string) => {
    const idx = messages.findIndex((m) => m.id === id);
    if (idx <= 0) return;
    const userMsg = [...messages].slice(0, idx).reverse().find((m) => m.role === "user");
    if (!userMsg) return;
    setMessages((prev) => prev.slice(0, idx));
    void send(userMsg.content);
  }, [messages, send]);

  const reset = useCallback(() => {
    setMessages([]);
    setPipeline({ status: "idle" });
    conversationId.current = uid();
    sessionStorage.removeItem(LAST_CHAT_CONVERSATION_STORAGE_KEY);
  }, []);

  return { messages, send, stop, retry, reset, streaming, pipeline, conversationId: conversationId.current };
}
