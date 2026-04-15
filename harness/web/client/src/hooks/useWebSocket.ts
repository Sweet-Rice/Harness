import { useEffect, useRef } from "react";
import { useStore } from "../store";

const WS_PORT = 8766;
const RECONNECT_BASE = 2000;
const RECONNECT_MAX = 30000;

declare global {
  interface Window {
    HARNESS_WS_URL?: string;
  }
}

function normalizeWebSocketUrl(raw: string) {
  if (!raw) return "";

  if (raw.startsWith("ws://") || raw.startsWith("wss://")) {
    return raw;
  }

  if (raw.startsWith("http://")) {
    return `ws://${raw.slice("http://".length)}`;
  }

  if (raw.startsWith("https://")) {
    return `wss://${raw.slice("https://".length)}`;
  }

  return raw;
}

function getWebSocketUrl() {
  const params = new URLSearchParams(location.search);
  const queryValue = params.get("ws") || "";
  const runtimeValue = window.HARNESS_WS_URL || "";
  const envValue = import.meta.env.VITE_WS_URL || "";
  const configured = normalizeWebSocketUrl(
    queryValue || runtimeValue || envValue
  );

  if (configured) {
    return configured;
  }

  const protocol = location.protocol === "https:" ? "wss" : "ws";
  return `${protocol}://${location.hostname}:${WS_PORT}`;
}

export function useWebSocket() {
  const setConnection = useStore((s) => s.setConnection);
  const setWs = useStore((s) => s.setWs);
  const retryDelay = useRef(RECONNECT_BASE);

  useEffect(() => {
    let ws: WebSocket;
    let reconnectTimer: ReturnType<typeof setTimeout>;
    let unmounted = false;

    function connect() {
      if (unmounted) return;

      const store = useStore.getState();
      store.setConnection("connecting");

      ws = new WebSocket(getWebSocketUrl());

      ws.onopen = () => {
        if (unmounted) return;
        useStore.getState().setConnection("connected");
        useStore.getState().setWs(ws);
        retryDelay.current = RECONNECT_BASE;
      };

      ws.onclose = () => {
        if (unmounted) return;
        useStore.getState().setConnection("disconnected");
        useStore.getState().setWs(null);
        reconnectTimer = setTimeout(() => {
          retryDelay.current = Math.min(
            retryDelay.current * 1.5,
            RECONNECT_MAX
          );
          connect();
        }, retryDelay.current);
      };

      ws.onmessage = (e) => {
        if (unmounted) return;
        const data = JSON.parse(e.data);
        dispatch(data);
      };
    }

    connect();

    return () => {
      unmounted = true;
      clearTimeout(reconnectTimer);
      ws?.close();
      setWs(null);
      setConnection("disconnected");
    };
  }, [setConnection, setWs]);
}

function dispatch(data: { type: string; content: unknown; current?: string }) {
  const store = useStore.getState();

  switch (data.type) {
    case "status":
      store.setAgentStatus(data.content as string);
      break;

    case "conversations":
      store.setConversations(
        data.content as Array<{
          id: string;
          name: string;
          message_count: number;
          created_at: string;
          updated_at: string;
        }>,
        (data.current as string) || ""
      );
      break;

    case "stream_start":
      store.streamStart();
      break;

    case "stream_token":
      store.streamToken(data.content as string);
      break;

    case "stream_thinking":
      store.streamThinking(data.content as string);
      break;

    case "stream_end":
      store.streamEnd();
      break;

    case "message": {
      const content = data.content as string;
      // Deduplicate: if stream already captured this content, skip
      if (store.lastStreamContent && content === store.lastStreamContent) {
        useStore.setState({ lastStreamContent: "" });
        return;
      }
      useStore.setState({ lastStreamContent: "" });
      store.addEvent({ type: "assistant", content });
      break;
    }

    case "user":
      store.addEvent({ type: "user", content: data.content as string });
      break;

    case "system":
      store.addEvent({ type: "system", content: data.content as string });
      break;

    case "log":
      store.addEvent({ type: "log", content: data.content as string });
      break;

    // Structured events
    case "tool_start": {
      const parsed = JSON.parse(data.content as string);
      store.toolCallStart(parsed.name, parsed.arguments);
      break;
    }

    case "tool_result": {
      const parsed = JSON.parse(data.content as string);
      store.toolCallResult(parsed.name, parsed.result, parsed.is_error);
      break;
    }

    case "delegation_start": {
      const parsed = JSON.parse(data.content as string);
      store.delegationStart(parsed.agent_name, parsed.task);
      break;
    }

    case "agent_start": {
      const parsed = JSON.parse(data.content as string);
      store.agentStart(parsed.agent_name);
      break;
    }

    case "agent_event": {
      const parsed = JSON.parse(data.content as string);
      store.addAgentEvent({
        eventType: parsed.event_type,
        content: parsed.content,
      });
      break;
    }

    case "agent_end": {
      const parsed = JSON.parse(data.content as string);
      store.agentEnd(parsed.agent_name, parsed.output_preview);
      break;
    }
  }
}
