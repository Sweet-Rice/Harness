import { useStore } from "../../store";

export function ContextPanel() {
  const open = useStore((s) => s.contextPanelOpen);
  const events = useStore((s) => s.events);
  const stream = useStore((s) => s.stream);

  if (!open) return null;

  return (
    <div
      style={{
        width: 320,
        background: "var(--bg-secondary)",
        borderLeft: "1px solid var(--border)",
        display: "flex",
        flexDirection: "column",
        flexShrink: 0,
      }}
    >
      <div
        style={{
          padding: "8px 12px",
          borderBottom: "1px solid var(--border)",
          fontSize: "0.8em",
          color: "var(--text-muted)",
          fontWeight: "bold",
        }}
      >
        Context
      </div>
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "4px 0",
          fontSize: "0.8em",
        }}
      >
        {events.map((ev, i) => (
          <ContextEntry key={i} event={ev} />
        ))}
        {stream.active && (
          <div
            style={{
              padding: "4px 12px",
              borderBottom: "1px solid rgba(51, 51, 51, 0.5)",
            }}
          >
            <RoleTag role="streaming" />
            <span style={{ color: "var(--text-muted)" }}>
              {stream.content.slice(0, 100)}
              {stream.content.length > 100 ? "..." : ""}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

function ContextEntry({
  event,
}: {
  event: {
    type: string;
    content?: string;
    data?: { name?: string; arguments?: Record<string, unknown>; result?: string; agentName?: string; task?: string };
  };
}) {
  let role = event.type;
  let text = "";

  switch (event.type) {
    case "user":
    case "assistant":
    case "system":
    case "log":
      text = (event as { content: string }).content || "";
      break;
    case "tool_call": {
      const d = event.data as { name: string; arguments: Record<string, unknown>; result?: string };
      role = "tool";
      text = `${d.name}(${JSON.stringify(d.arguments)})`;
      if (d.result) text += ` => ${d.result.slice(0, 100)}`;
      break;
    }
    case "delegation": {
      const d = event.data as { agentName: string; task: string };
      role = "delegate";
      text = `${d.agentName}: ${d.task}`;
      break;
    }
    default:
      text = JSON.stringify(event);
  }

  return (
    <div
      style={{
        padding: "4px 12px",
        borderBottom: "1px solid rgba(51, 51, 51, 0.5)",
        whiteSpace: "nowrap",
        overflow: "hidden",
        textOverflow: "ellipsis",
      }}
      title={text}
    >
      <RoleTag role={role} />
      <span style={{ color: "var(--text-primary)" }}>
        {text.slice(0, 120)}
        {text.length > 120 ? "..." : ""}
      </span>
    </div>
  );
}

function RoleTag({ role }: { role: string }) {
  const colors: Record<string, string> = {
    user: "var(--accent-blue)",
    assistant: "var(--text-primary)",
    system: "var(--accent-orange)",
    log: "var(--text-muted)",
    tool: "var(--accent-blue)",
    delegate: "var(--accent-purple)",
    streaming: "var(--accent-orange)",
  };

  return (
    <span
      style={{
        color: colors[role] || "var(--text-muted)",
        marginRight: 6,
        fontSize: "0.85em",
        opacity: 0.8,
      }}
    >
      [{role}]
    </span>
  );
}
