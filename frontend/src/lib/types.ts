/**
 * EN: Shared TypeScript types mirroring backend AgentState / SSE payloads.
 * PT: Tipos TypeScript alinhados com AgentState e eventos SSE do backend.
 */
export type AgentVersion = "v1" | "v2";

export interface Source {
  url: string;
  title: string;
  snippet: string;
  domain: string;
  score: number;
  source_type: "web" | "labor_code_index" | "calculator";
}

export interface ToolCallTrace {
  tool_name: string;
  args: Record<string, unknown>;
  output_summary: string;
  duration_ms: number;
  success: boolean;
  error: string | null;
}

export type AgentEvent =
  | { type: "start"; conversation_id: string; agent_version: AgentVersion }
  | { type: "phase"; phase: string; message: string }
  | { type: "category"; category: string }
  | {
      type: "tool_call";
      tool: string;
      args: Record<string, unknown>;
      summary: string;
      duration_ms: number;
      success: boolean;
      error: string | null;
    }
  | { type: "sources"; sources: Source[] }
  | { type: "token"; delta: string }
  | { type: "confidence"; score: number }
  | { type: "refusal"; answer: string }
  | { type: "done"; state: AgentState }
  | { type: "error"; message: string };

export interface AgentState {
  user_query: string;
  conversation_id: string;
  category?: string;
  final_answer: string;
  confidence: number;
  refused: boolean;
  refusal_reason?: string | null;
  iterations: number;
  sources: Source[];
  tool_traces: ToolCallTrace[];
  agent_version: AgentVersion;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  streaming?: boolean;
  phase?: string;
  category?: string;
  toolCalls?: ToolCallTrace[];
  sources?: Source[];
  confidence?: number;
  refused?: boolean;
  agentVersion?: AgentVersion;
  createdAt: number;
}

export interface EvalSummary {
  n: number;
  correctness_avg: number;
  coverage_avg: number;
  citation_quality_avg: number;
  refusal_accuracy: number;
  tool_call_accuracy: number;
  latency_p50_ms: number;
  latency_p95_ms: number;
  by_difficulty: Record<string, number>;
}

export interface EvalDelta {
  v1: EvalSummary;
  v2: EvalSummary;
  delta: Record<
    string,
    { v1: number; v2: number; delta: number; delta_pct: number }
  >;
}
