"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { v4 as uuidv4 } from "uuid";

import { Header } from "@/components/Header";
import { ChatInput } from "./ChatInput";
import { MessageBubble } from "./MessageBubble";
import { WelcomeHero } from "./WelcomeHero";
import { streamChat } from "@/lib/api";
import type {
  AgentEvent,
  AgentVersion,
  ChatMessage,
  Source,
  ToolCallTrace,
} from "@/lib/types";

const STARTERS = [
  "Qual é o salário mínimo nacional atual em Portugal?",
  "Como se calcula o subsídio de férias para 1.500 EUR/mês?",
  "Que prazo de aviso prévio é necessário para 3 anos de antiguidade?",
  "É legal uma cláusula de não concorrência de 3 anos?",
];

export function ChatContainer() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [version, setVersion] = useState<AgentVersion>("v2");
  const [isStreaming, setIsStreaming] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages]);

  const send = useCallback(
    async (text: string) => {
      if (isStreaming) return;
      const userMsg: ChatMessage = {
        id: uuidv4(),
        role: "user",
        content: text,
        createdAt: Date.now(),
      };
      const assistantId = uuidv4();
      const assistantMsg: ChatMessage = {
        id: assistantId,
        role: "assistant",
        content: "",
        streaming: true,
        toolCalls: [],
        sources: [],
        agentVersion: version,
        createdAt: Date.now(),
      };
      setMessages((prev) => [...prev, userMsg, assistantMsg]);
      setIsStreaming(true);

      const controller = new AbortController();
      abortRef.current = controller;

      try {
        for await (const ev of streamChat(
          text,
          conversationId,
          version,
          controller.signal
        )) {
          handleEvent(ev, assistantId, setMessages, setConversationId);
        }
      } catch (err) {
        const msg =
          err instanceof Error ? err.message : "Erro de comunicação.";
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? {
                  ...m,
                  content:
                    m.content ||
                    `**Erro de comunicação com o backend.**\n\n\`${msg}\`\n\nVerifique se o servidor está em execução em \`${
                      process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
                    }\`.`,
                  streaming: false,
                }
              : m
          )
        );
      } finally {
        setIsStreaming(false);
        abortRef.current = null;
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId ? { ...m, streaming: false } : m
          )
        );
      }
    },
    [conversationId, isStreaming, version]
  );

  const stop = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  const newChat = useCallback(() => {
    abortRef.current?.abort();
    setMessages([]);
    setConversationId(null);
  }, []);

  const showHero = useMemo(() => messages.length === 0, [messages.length]);

  return (
    <div className="flex flex-col min-h-screen">
      <Header version={version} onVersionChange={setVersion} />
      <main className="flex-1 flex flex-col">
        <div
          ref={scrollRef}
          className="flex-1 overflow-y-auto"
        >
          <div className="container max-w-3xl py-4 md:py-8">
            {showHero ? (
              <WelcomeHero />
            ) : (
              <div>
                {messages.map((m, i) => (
                  <MessageBubble key={m.id} message={m} index={i} />
                ))}
              </div>
            )}
          </div>
        </div>
        <div className="sticky bottom-0 bg-bg border-t border-border pt-4">
          <div className="container max-w-3xl pb-4">
            <div className="flex items-center justify-between mb-2">
              <button
                onClick={newChat}
                className="text-[11px] text-ink-dim hover:text-ink transition"
              >
                + Nova conversa
              </button>
              {conversationId && (
                <span className="text-[10px] font-mono text-ink-dim">
                  conv: {conversationId.slice(0, 8)}…
                </span>
              )}
            </div>
            <ChatInput
              onSend={send}
              onStop={stop}
              isStreaming={isStreaming}
              suggestions={showHero ? STARTERS : undefined}
            />
          </div>
        </div>
      </main>
    </div>
  );
}

// ---- Event reducer ---- //

function handleEvent(
  ev: AgentEvent,
  targetId: string,
  setMessages: React.Dispatch<React.SetStateAction<ChatMessage[]>>,
  setConversationId: (id: string) => void
) {
  setMessages((prev) =>
    prev.map((m) => {
      if (m.id !== targetId) return m;
      switch (ev.type) {
        case "start":
          setConversationId(ev.conversation_id);
          return { ...m, agentVersion: ev.agent_version };
        case "phase":
          return { ...m, phase: ev.phase };
        case "category":
          return { ...m, category: ev.category };
        case "tool_call": {
          const trace: ToolCallTrace = {
            tool_name: ev.tool,
            args: ev.args,
            output_summary: ev.summary,
            duration_ms: ev.duration_ms,
            success: ev.success,
            error: ev.error,
          };
          return { ...m, toolCalls: [...(m.toolCalls || []), trace] };
        }
        case "sources": {
          const merged: Source[] = [...(m.sources || []), ...ev.sources];
          // dedupe by url
          const seen = new Set<string>();
          const dedup = merged.filter((s) => {
            const k = s.url || s.title;
            if (seen.has(k)) return false;
            seen.add(k);
            return true;
          });
          return { ...m, sources: dedup };
        }
        case "token":
          return { ...m, content: m.content + ev.delta };
        case "confidence":
          return { ...m, confidence: ev.score };
        case "refusal":
          return { ...m, content: ev.answer, refused: true };
        case "done":
          return {
            ...m,
            confidence: ev.state.confidence,
            refused: ev.state.refused,
            sources: ev.state.sources,
            toolCalls: ev.state.tool_traces,
            agentVersion: ev.state.agent_version,
            phase: undefined,
          };
        case "error":
          return {
            ...m,
            content:
              m.content ||
              `**Erro do agente.**\n\n\`${ev.message}\``,
          };
        default:
          return m;
      }
    })
  );
}
