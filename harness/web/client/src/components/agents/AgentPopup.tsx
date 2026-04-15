import { useEffect, useCallback } from "react";
import { useStore } from "../../store";

export function AgentPopup() {
  const open = useStore((s) => s.agentPopupOpen);
  const close = useStore((s) => s.closeAgentPopup);
  const delegation = useStore((s) => s.activeDelegation);
  const agentEvents = useStore((s) => s.agentEvents);

  // Find the most recent delegation from events if activeDelegation is null
  const events = useStore((s) => s.events);
  const lastDelegation = delegation || (() => {
    for (let i = events.length - 1; i >= 0; i--) {
      const ev = events[i];
      if (ev.type === "delegation") return ev.data;
    }
    return null;
  })();

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Escape") close();
    },
    [close]
  );

  useEffect(() => {
    if (open) {
      document.addEventListener("keydown", handleKeyDown);
      return () => document.removeEventListener("keydown", handleKeyDown);
    }
  }, [open, handleKeyDown]);

  if (!open) return null;

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0, 0, 0, 0.7)",
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        zIndex: 100,
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) close();
      }}
    >
      <div
        style={{
          background: "var(--bg-primary)",
          border: "1px solid var(--accent-purple)",
          borderRadius: 8,
          width: "80%",
          maxWidth: 900,
          height: "80%",
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: "12px 16px",
            borderBottom: "1px solid var(--border)",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <div>
            <span
              style={{
                color: "var(--accent-purple)",
                fontWeight: "bold",
                fontSize: "1.1em",
              }}
            >
              agent:{lastDelegation?.agentName || "unknown"}
            </span>
            <span
              style={{
                color: "var(--text-muted)",
                fontSize: "0.85em",
                marginLeft: 12,
              }}
            >
              {lastDelegation?.status === "running" ? "running..." : "completed"}
            </span>
          </div>
          <button
            onClick={close}
            style={{
              background: "none",
              border: "1px solid var(--border)",
              color: "var(--text-secondary)",
              padding: "4px 10px",
              cursor: "pointer",
              fontFamily: "var(--font-mono)",
              borderRadius: 3,
            }}
          >
            ESC
          </button>
        </div>

        {/* Task */}
        {lastDelegation?.task && (
          <div
            style={{
              padding: "8px 16px",
              borderBottom: "1px solid var(--border)",
              fontSize: "0.85em",
              color: "var(--text-secondary)",
            }}
          >
            <span style={{ color: "var(--text-muted)" }}>task: </span>
            {lastDelegation.task}
          </div>
        )}

        {/* Event log */}
        <div
          style={{
            flex: 1,
            overflowY: "auto",
            padding: 16,
          }}
        >
          {agentEvents.length === 0 && (
            <div style={{ color: "var(--text-muted)", fontStyle: "italic" }}>
              {lastDelegation?.status === "running"
                ? "Waiting for agent events..."
                : "No events recorded."}
            </div>
          )}
          {agentEvents.map((ev, i) => (
            <AgentEventRow key={i} eventType={ev.eventType} content={ev.content} />
          ))}
        </div>
      </div>
    </div>
  );
}

function AgentEventRow({
  eventType,
  content,
}: {
  eventType: string;
  content: string;
}) {
  const getColor = () => {
    switch (eventType) {
      case "stream_thinking":
        return "var(--accent-purple)";
      case "stream_token":
        return "var(--text-primary)";
      case "tool_start":
      case "tool_result":
        return "var(--accent-blue)";
      case "log":
        return "var(--text-muted)";
      case "status":
        return "var(--accent-orange)";
      case "message":
        return "var(--text-primary)";
      default:
        return "var(--text-muted)";
    }
  };

  // Skip stream_start/stream_end noise
  if (eventType === "stream_start" || eventType === "stream_end") return null;

  return (
    <div
      style={{
        padding: "3px 0",
        fontSize: "0.85em",
        display: "flex",
        gap: 8,
      }}
    >
      <span
        style={{
          color: "var(--text-muted)",
          fontSize: "0.8em",
          flexShrink: 0,
          minWidth: 100,
        }}
      >
        {eventType}
      </span>
      <span
        style={{
          color: getColor(),
          whiteSpace: "pre-wrap",
          wordBreak: "break-word",
          flex: 1,
        }}
      >
        {content.length > 500 ? content.slice(0, 500) + "..." : content}
      </span>
    </div>
  );
}
