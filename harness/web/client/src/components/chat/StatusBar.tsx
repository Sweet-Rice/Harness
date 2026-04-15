import { useStore } from "../../store";

export function StatusBar() {
  const connection = useStore((s) => s.connection);
  const toggleContext = useStore((s) => s.toggleContextPanel);
  const contextOpen = useStore((s) => s.contextPanelOpen);

  return (
    <div
      style={{
        padding: "4px 16px",
        fontSize: "0.8em",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        borderBottom: "1px solid var(--border)",
      }}
    >
      <span
        style={{
          color:
            connection === "connected"
              ? "var(--accent-green)"
              : "var(--accent-red)",
        }}
      >
        {connection}
      </span>
      <button
        onClick={toggleContext}
        style={{
          background: contextOpen ? "var(--accent-blue)" : "transparent",
          color: contextOpen ? "var(--bg-primary)" : "var(--text-secondary)",
          border: "1px solid var(--border)",
          padding: "2px 8px",
          fontFamily: "var(--font-mono)",
          fontSize: "0.85em",
          cursor: "pointer",
          borderRadius: 3,
        }}
      >
        ctx
      </button>
    </div>
  );
}
