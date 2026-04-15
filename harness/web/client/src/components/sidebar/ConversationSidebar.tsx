import { useStore } from "../../store";

export function ConversationSidebar() {
  const conversations = useStore((s) => s.conversations);
  const currentId = useStore((s) => s.currentConversationId);
  const sendCommand = useStore((s) => s.sendCommand);
  const clearEvents = useStore((s) => s.clearEvents);

  const handleNew = () => {
    sendCommand("new");
    clearEvents();
  };

  const handleLoad = (id: string) => {
    clearEvents();
    sendCommand("load", { id });
  };

  const handleDelete = (id: string) => {
    sendCommand("delete", { id });
  };

  return (
    <div
      style={{
        width: 220,
        background: "var(--bg-secondary)",
        borderRight: "1px solid var(--border)",
        display: "flex",
        flexDirection: "column",
        flexShrink: 0,
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: 12,
          borderBottom: "1px solid var(--border)",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          fontSize: "0.9em",
          color: "var(--text-secondary)",
        }}
      >
        <span>Conversations</span>
        <button
          onClick={handleNew}
          style={{
            background: "var(--accent-blue)",
            color: "var(--bg-primary)",
            border: "none",
            padding: "4px 10px",
            fontFamily: "var(--font-mono)",
            fontSize: "0.85em",
            cursor: "pointer",
            borderRadius: 3,
          }}
        >
          + New
        </button>
      </div>

      {/* List */}
      <div style={{ flex: 1, overflowY: "auto", padding: "4px 0" }}>
        {conversations.map((c) => (
          <div
            key={c.id}
            style={{
              padding: "8px 12px",
              cursor: "pointer",
              fontSize: "0.85em",
              color: c.id === currentId ? "var(--text-primary)" : "var(--text-secondary)",
              borderLeft:
                c.id === currentId
                  ? "3px solid var(--accent-blue)"
                  : "3px solid transparent",
              background: c.id === currentId ? "#1e1e1e" : "transparent",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
            onMouseEnter={(e) => {
              if (c.id !== currentId)
                e.currentTarget.style.background = "#1e1e1e";
            }}
            onMouseLeave={(e) => {
              if (c.id !== currentId)
                e.currentTarget.style.background = "transparent";
            }}
          >
            <span onClick={() => handleLoad(c.id)}>
              {c.name} ({c.message_count})
            </span>
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleDelete(c.id);
              }}
              style={{
                background: "none",
                border: "none",
                color: "#666",
                cursor: "pointer",
                fontSize: "0.9em",
                padding: "0 4px",
                fontFamily: "var(--font-mono)",
              }}
              onMouseEnter={(e) =>
                (e.currentTarget.style.color = "var(--accent-red)")
              }
              onMouseLeave={(e) => (e.currentTarget.style.color = "#666")}
            >
              x
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
