export type ConnectionStatus = "disconnected" | "connecting" | "connected";

export interface Conversation {
  id: string;
  name: string;
  message_count: number;
  created_at: string;
  updated_at: string;
}

export interface ToolCallData {
  name: string;
  arguments: Record<string, unknown>;
  result?: string;
  isError?: boolean;
  status: "running" | "done" | "error";
}

export interface DelegationData {
  agentName: string;
  task: string;
  status: "running" | "done";
  outputPreview?: string;
}

export type ChatEvent =
  | { type: "user"; content: string }
  | { type: "assistant"; content: string; thinking?: string }
  | { type: "tool_call"; data: ToolCallData }
  | { type: "delegation"; data: DelegationData }
  | { type: "system"; content: string }
  | { type: "log"; content: string };

export interface AgentEventEntry {
  eventType: string;
  content: string;
}

export interface StreamState {
  active: boolean;
  content: string;
  thinking: string;
}
