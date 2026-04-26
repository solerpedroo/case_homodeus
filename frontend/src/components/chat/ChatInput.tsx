"use client";

import { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";

interface Props {
  onSend: (text: string) => void;
  onStop: () => void;
  isStreaming: boolean;
  disabled?: boolean;
  suggestions?: string[];
}

export function ChatInput({
  onSend,
  onStop,
  isStreaming,
  disabled,
  suggestions,
}: Props) {
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
    <div>
      {suggestions && suggestions.length > 0 && !value && !isStreaming && (
        <div className="mb-4">
          <div className="marker mb-2">/sugestões</div>
          <ul className="space-y-1.5">
            {suggestions.map((s) => (
              <li key={s}>
                <button
                  onClick={() => onSend(s)}
                  className="group text-left text-[14px] text-ink-muted hover:text-ink transition-colors"
                >
                  <span className="text-ink-dim mr-2">·</span>
                  <span className="group-hover:underline underline-offset-4 decoration-ink-dim">
                    {s}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div
        className={cn(
          "flex items-end gap-3 border-b border-border-strong",
          "focus-within:border-ink transition-colors",
          "py-2"
        )}
      >
        <span className="font-mono text-ink-dim text-sm pb-1.5 select-none">
          &gt;
        </span>
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
          placeholder="Pergunte sobre direito laboral português ou processamento salarial."
          disabled={disabled}
          className={cn(
            "flex-1 resize-none bg-transparent outline-none",
            "text-[15px] text-ink placeholder:text-ink-dim",
            "max-h-[200px] py-1"
          )}
        />
        {isStreaming ? (
          <button
            onClick={onStop}
            className="font-mono text-[13px] text-ink-muted hover:text-danger transition-colors pb-1.5"
            title="Parar"
          >
            esc ⨯
          </button>
        ) : (
          <button
            onClick={submit}
            disabled={!value.trim() || disabled}
            className={cn(
              "font-mono text-base pb-1 transition-colors",
              value.trim() && !disabled
                ? "text-ink hover:text-accent"
                : "text-ink-dim cursor-not-allowed"
            )}
            title="Enviar (Enter)"
          >
            ↵
          </button>
        )}
      </div>
      <div className="mt-2 text-[10px] font-mono text-ink-dim">
        shift+enter — nova linha
      </div>
    </div>
  );
}

function autosize(el: HTMLTextAreaElement | null) {
  if (!el) return;
  el.style.height = "auto";
  el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
}
