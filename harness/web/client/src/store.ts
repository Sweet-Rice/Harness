import { create } from "zustand";
import type {
  ChatEvent,
  ConnectionStatus,
  Conversation,
  StreamState,
  ToolCallData,
  DelegationData,
  AgentEventEntry,
} from "./types";

interface HarnessStore {
  // Connection
  connection: ConnectionStatus;
  setConnection: (s: ConnectionStatus) => void;

  // Agent status
  agentStatus: string;
  setAgentStatus: (s: string) => void;

  // Main timeline
  events: ChatEvent[];
  addEvent: (e: ChatEvent) => void;
  clearEvents: () => void;

  // Streaming (ephemeral)
  stream: StreamState;
  streamStart: () => void;
  streamToken: (token: string) => void;
  streamThinking: (token: string) => void;
  streamEnd: () => void;
  lastStreamContent: string;

  // Tool calls in flight
  toolCallStart: (name: string, args: Record<string, unknown>) => void;
  toolCallResult: (name: string, result: string, isError: boolean) => void;

  // Delegation
  activeDelegation: DelegationData | null;
  agentEvents: AgentEventEntry[];
  delegationStart: (agentName: string, task: string) => void;
  agentStart: (agentName: string) => void;
  addAgentEvent: (entry: AgentEventEntry) => void;
  agentEnd: (agentName: string, outputPreview: string) => void;

  // Conversations
  conversations: Conversation[];
  currentConversationId: string | null;
  setConversations: (convos: Conversation[], currentId: string) => void;

  // UI toggles
  contextPanelOpen: boolean;
  toggleContextPanel: () => void;
  agentPopupOpen: boolean;
  openAgentPopup: () => void;
  closeAgentPopup: () => void;

  // WebSocket
  ws: WebSocket | null;
  setWs: (ws: WebSocket | null) => void;
  sendMessage: (content: string) => void;
  sendCommand: (cmd: string, params?: Record<string, string>) => void;
}

export const useStore = create<HarnessStore>((set, get) => ({
  // Connection
  connection: "disconnected",
  setConnection: (s) => set({ connection: s }),

  // Agent status
  agentStatus: "idle",
  setAgentStatus: (s) => set({ agentStatus: s }),

  // Events
  events: [],
  addEvent: (e) => set((s) => ({ events: [...s.events, e] })),
  clearEvents: () => set({ events: [] }),

  // Stream
  stream: { active: false, content: "", thinking: "" },
  lastStreamContent: "",

  streamStart: () =>
    set({ stream: { active: true, content: "", thinking: "" } }),

  streamToken: (token) =>
    set((s) => ({
      stream: { ...s.stream, content: s.stream.content + token },
    })),

  streamThinking: (token) =>
    set((s) => ({
      stream: { ...s.stream, thinking: s.stream.thinking + token },
    })),

  streamEnd: () => {
    const { stream } = get();
    if (stream.content) {
      const event: ChatEvent = {
        type: "assistant",
        content: stream.content,
        thinking: stream.thinking || undefined,
      };
      set((s) => ({
        events: [...s.events, event],
        stream: { active: false, content: "", thinking: "" },
        lastStreamContent: stream.content,
      }));
    } else {
      set({ stream: { active: false, content: "", thinking: "" } });
    }
  },

  // Tool calls
  toolCallStart: (name, args) => {
    const tc: ToolCallData = {
      name,
      arguments: args,
      status: "running",
    };
    set((s) => ({ events: [...s.events, { type: "tool_call", data: tc }] }));
  },

  toolCallResult: (name, result, isError) => {
    set((s) => {
      const events = [...s.events];
      for (let i = events.length - 1; i >= 0; i--) {
        const ev = events[i];
        if (
          ev.type === "tool_call" &&
          ev.data.name === name &&
          ev.data.status === "running"
        ) {
          events[i] = {
            ...ev,
            data: {
              ...ev.data,
              result,
              isError,
              status: isError ? "error" : "done",
            },
          };
          break;
        }
      }
      return { events };
    });
  },

  // Delegation
  activeDelegation: null,
  agentEvents: [],

  delegationStart: (agentName, task) => {
    const d: DelegationData = { agentName, task, status: "running" };
    set((s) => ({
      activeDelegation: d,
      agentEvents: [],
      events: [...s.events, { type: "delegation", data: d }],
    }));
  },

  agentStart: () => {},

  addAgentEvent: (entry) =>
    set((s) => ({ agentEvents: [...s.agentEvents, entry] })),

  agentEnd: (agentName, outputPreview) => {
    set((s) => {
      const events = [...s.events];
      for (let i = events.length - 1; i >= 0; i--) {
        const ev = events[i];
        if (
          ev.type === "delegation" &&
          ev.data.agentName === agentName &&
          ev.data.status === "running"
        ) {
          events[i] = {
            ...ev,
            data: { ...ev.data, status: "done", outputPreview },
          };
          break;
        }
      }
      return { events, activeDelegation: null };
    });
  },

  // Conversations
  conversations: [],
  currentConversationId: null,
  setConversations: (convos, currentId) =>
    set({ conversations: convos, currentConversationId: currentId }),

  // UI
  contextPanelOpen: false,
  toggleContextPanel: () =>
    set((s) => ({ contextPanelOpen: !s.contextPanelOpen })),
  agentPopupOpen: false,
  openAgentPopup: () => set({ agentPopupOpen: true }),
  closeAgentPopup: () => set({ agentPopupOpen: false }),

  // WebSocket
  ws: null,
  setWs: (ws) => set({ ws }),

  sendMessage: (content) => {
    const { ws } = get();
    if (ws && ws.readyState === WebSocket.OPEN) {
      set((s) => ({
        events: [...s.events, { type: "user", content }],
      }));
      ws.send(JSON.stringify({ content }));
    }
  },

  sendCommand: (cmd, params) => {
    const { ws } = get();
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ command: cmd, ...params }));
    }
  },
}));
