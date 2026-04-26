"use client";

import { motion } from "framer-motion";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Bot, User } from "lucide-react";
import type { ChatMessage } from "@/lib/types";
import { cn } from "@/lib/utils";
import { ToolCallCard } from "./ToolCallCard";
import { SourceList } from "./SourceCard";
import { ConfidenceBadge } from "./ConfidenceBadge";
import { PhaseIndicator } from "./PhaseIndicator";

interface Props {
  message: ChatMessage;
}

export function MessageBubble({ message }: Props) {
  const isUser = message.role === "user";
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: [0.2, 0.8, 0.2, 1] }}
      className={cn(
        "flex gap-3 px-1 py-3",
        isUser ? "justify-end" : "justify-start"
      )}
    >
      {!isUser && (
        <Avatar variant="assistant" />
      )}
      <div className={cn("max-w-[78%] min-w-0", isUser && "text-right")}>
        <div
          className={cn(
            "inline-block text-left rounded-2xl px-4 py-3 border",
            isUser
              ? "bg-accent text-white border-accent/40 shadow-[0_4px_24px_rgba(124,92,255,0.25)]"
              : "bg-bg-panel border-border"
          )}
        >
          {!isUser && message.category && (
            <div className="mb-2 inline-flex items-center gap-1.5 text-[10px] uppercase tracking-[0.18em] text-ink-dim">
              <span className="w-1 h-1 rounded-full bg-accent inline-block" />
              {message.category}
            </div>
          )}

          {!isUser && message.toolCalls && message.toolCalls.length > 0 && (
            <div className="mb-3 space-y-1.5">
              {message.toolCalls.map((t, i) => (
                <ToolCallCard key={`${t.tool_name}-${i}`} trace={t} />
              ))}
            </div>
          )}

          <div
            className={cn(
              "prose-chat text-sm",
              isUser && "text-white/95"
            )}
          >
            {message.content ? (
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {message.content}
              </ReactMarkdown>
            ) : message.streaming && message.phase ? (
              <PhaseIndicator phase={message.phase} />
            ) : null}
            {message.streaming && message.content && (
              <span className="inline-block w-1.5 h-4 ml-0.5 align-middle bg-accent-glow animate-pulse rounded-sm" />
            )}
          </div>

          {!isUser && message.sources && message.sources.length > 0 && (
            <SourceList sources={message.sources} />
          )}

          {!isUser &&
            (typeof message.confidence === "number" ||
              message.refused) && (
              <div className="mt-3 flex items-center justify-between gap-2 flex-wrap">
                <ConfidenceBadge
                  score={message.confidence ?? 0}
                  refused={message.refused}
                />
                {message.agentVersion && (
                  <span className="text-[10px] font-mono uppercase tracking-wider text-ink-dim">
                    {message.agentVersion}
                  </span>
                )}
              </div>
            )}
        </div>
      </div>
      {isUser && <Avatar variant="user" />}
    </motion.div>
  );
}

function Avatar({ variant }: { variant: "user" | "assistant" }) {
  if (variant === "user") {
    return (
      <div className="w-8 h-8 rounded-full grid place-items-center bg-bg-elevated border border-border shrink-0">
        <User className="w-4 h-4 text-ink-muted" />
      </div>
    );
  }
  return (
    <div className="w-8 h-8 rounded-full grid place-items-center bg-gradient-to-br from-accent to-accent-glow shrink-0 shadow-[0_0_18px_rgba(124,92,255,0.45)]">
      <Bot className="w-4 h-4 text-white" />
    </div>
  );
}
