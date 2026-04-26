"use client";

import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { ArrowUp, Square } from "lucide-react";
import { cn } from "@/lib/utils";

interface Props {
  onSend: (text: string) => void;
  onStop: () => void;
  isStreaming: boolean;
  disabled?: boolean;
  suggestions?: string[];
}

export function ChatInput({ onSend, onStop, isStreaming, disabled, suggestions }: Props) {
  const [value, setValue] = useState("");
  const ref = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    autosize(ref.current);
  }, [value]);

  const submit = () => {
    const v = value.trim();
    if (!v || isStreaming || disabled) return;
    onSend(v);
    setValue("");
    if (ref.current) ref.current.style.height = "auto";
  };

  return (
    <div className="space-y-2">
      {suggestions && suggestions.length > 0 && !value && !isStreaming && (
        <div className="flex flex-wrap gap-2">
          {suggestions.map((s) => (
            <button
              key={s}
              onClick={() => onSend(s)}
              className="px-3 py-1.5 text-xs rounded-full border border-border bg-bg-elevated/40 hover:bg-bg-elevated hover:border-accent/40 text-ink-muted hover:text-ink transition"
            >
              {s}
            </button>
          ))}
        </div>
      )}
      <motion.div
        layout
        className={cn(
          "relative flex items-end gap-2 rounded-2xl border border-border",
          "bg-bg-panel focus-within:border-accent/60 transition",
          "shadow-[0_8px_32px_rgba(0,0,0,0.35)]",
          "px-3 py-2.5"
        )}
      >
        <textarea
          ref={ref}
          rows={1}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              submit();
            }
          }}
          placeholder="Pergunte sobre direito laboral português ou processamento salarial…"
          disabled={disabled}
          className={cn(
            "flex-1 resize-none bg-transparent outline-none",
            "text-sm text-ink placeholder:text-ink-dim",
            "max-h-[200px] py-1.5"
          )}
        />
        {isStreaming ? (
          <button
            onClick={onStop}
            className="grid place-items-center w-9 h-9 rounded-xl bg-danger text-white hover:opacity-90 transition shrink-0"
            title="Parar"
          >
            <Square className="w-4 h-4" fill="currentColor" />
          </button>
        ) : (
          <button
            onClick={submit}
            disabled={!value.trim() || disabled}
            className={cn(
              "grid place-items-center w-9 h-9 rounded-xl shrink-0 transition",
              value.trim() && !disabled
                ? "bg-accent text-white shadow-[0_0_14px_rgba(124,92,255,0.45)] hover:shadow-[0_0_22px_rgba(124,92,255,0.65)]"
                : "bg-bg-elevated text-ink-dim cursor-not-allowed"
            )}
            title="Enviar"
          >
            <ArrowUp className="w-4 h-4" strokeWidth={2.4} />
          </button>
        )}
      </motion.div>
      <div className="text-[10px] text-ink-dim text-center">
        Shift+Enter para nova linha · Respostas geradas por IA — verifica sempre as fontes oficiais.
      </div>
    </div>
  );
}

function autosize(el: HTMLTextAreaElement | null) {
  if (!el) return;
  el.style.height = "auto";
  el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
}
