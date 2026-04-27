"use client";

/**
 * EN: User/assistant bubble — markdown answer via react-markdown, tool cards,
 *     source list, confidence badge.
 * PT: Bolha user/assistant — markdown, cartões de ferramentas, fontes, confiança.
 */

import { motion } from "framer-motion";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { ChatMessage } from "@/lib/types";
import { cn } from "@/lib/utils";
import { ToolCallCard } from "./ToolCallCard";
import { SourceList } from "./SourceCard";
import { ConfidenceBadge } from "./ConfidenceBadge";
import { PhaseIndicator } from "./PhaseIndicator";
import { useT } from "@/lib/i18n";

interface Props {
  message: ChatMessage;
  index?: number;
}

export function MessageBubble({ message, index }: Props) {
  const t = useT();
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, ease: [0.2, 0.8, 0.2, 1] }}
        className="py-6"
      >
        <div className="marker mb-2">
          {t.chat.youMarker}{" "}
          {typeof index === "number" ? formatIndex(index) : ""}
        </div>
        <div className="text-[15px] text-ink leading-relaxed font-medium tracking-tight">
          {message.content}
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: [0.2, 0.8, 0.2, 1] }}
      className="py-6 border-t border-border"
    >
      <div className="flex items-center justify-between mb-4">
        <div className="marker">
          {t.chat.responseMarker}{" "}
          {message.category ? `· ${message.category}` : ""}
        </div>
        {message.agentVersion && (
          <span className="font-mono text-[10px] uppercase tracking-marker text-ink-dim">
            {message.agentVersion}
          </span>
        )}
      </div>

      {message.toolCalls && message.toolCalls.length > 0 && (
        <div className="mb-5 space-y-1">
          {message.toolCalls.map((t, i) => (
            <ToolCallCard key={`${t.tool_name}-${i}`} trace={t} />
          ))}
        </div>
      )}

      <div className={cn("prose-chat")}>
        {message.content ? (
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {message.content}
          </ReactMarkdown>
        ) : message.streaming && message.phase ? (
          <PhaseIndicator phase={message.phase} />
        ) : null}
        {message.streaming && message.content && (
          <span className="cursor-blink" />
        )}
      </div>

      {message.sources && message.sources.length > 0 && (
        <SourceList sources={message.sources} />
      )}

      {(typeof message.confidence === "number" || message.refused) && (
        <div className="mt-5 pt-4 border-t border-border">
          <ConfidenceBadge
            score={message.confidence ?? 0}
            refused={message.refused}
          />
        </div>
      )}
    </motion.div>
  );
}

function formatIndex(i: number): string {
  return String(i + 1).padStart(2, "0");
}
