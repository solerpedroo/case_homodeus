import type { AgentEvent, AgentVersion } from "./types";
import type { Locale } from "./i18n";

export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function* streamChat(
  message: string,
  conversationId: string | null,
  version: AgentVersion,
  signal: AbortSignal,
  locale: Locale = "pt"
): AsyncGenerator<AgentEvent> {
  const params = new URLSearchParams({
    message,
    agent_version: version,
    locale,
  });
  if (conversationId) params.set("conversation_id", conversationId);
  const url = `${API_BASE}/chat/stream?${params.toString()}`;

  const resp = await fetch(url, {
    method: "GET",
    headers: { Accept: "text/event-stream" },
    signal,
  });
  if (!resp.ok || !resp.body) {
    throw new Error(`Stream error ${resp.status}: ${await resp.text()}`);
  }

  const reader = resp.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const blocks = buffer.split("\n\n");
    buffer = blocks.pop() || "";
    for (const block of blocks) {
      const line = block.split("\n").find((l) => l.startsWith("data:"));
      if (!line) continue;
      const json = line.replace(/^data:\s*/, "");
      if (!json) continue;
      try {
        yield JSON.parse(json) as AgentEvent;
      } catch {
        // ignore malformed chunks
      }
    }
  }
}

export async function fetchEvalResults(): Promise<{
  v1: unknown;
  v2: unknown;
}> {
  const r = await fetch(`${API_BASE}/eval/results`, { cache: "no-store" });
  if (!r.ok) throw new Error(`eval results: ${r.status}`);
  return r.json();
}

export async function fetchEvalCases(): Promise<unknown[]> {
  const r = await fetch(`${API_BASE}/eval/cases`, { cache: "no-store" });
  if (!r.ok) throw new Error(`eval cases: ${r.status}`);
  return r.json();
}

export async function runEval(version: AgentVersion, concurrency = 4) {
  const r = await fetch(`${API_BASE}/eval/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ agent_version: version, concurrency }),
  });
  if (!r.ok) throw new Error(`run eval: ${r.status}`);
  return r.json();
}
