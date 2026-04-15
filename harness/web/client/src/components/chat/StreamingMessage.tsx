import { useStore } from "../../store";

export function StreamingMessage() {
  const stream = useStore((s) => s.stream);

  if (!stream.active) return null;

  return (
    <div style={{ padding: "6px 0" }}>
      {stream.thinking && (
        <div
          style={{
            color: "var(--accent-purple)",
            fontSize: "0.85em",
            fontStyle: "italic",
            borderLeft: "2px solid var(--accent-purple)",
            paddingLeft: 8,
            marginBottom: 4,
            maxHeight: 150,
            overflowY: "auto",
            whiteSpace: "pre-wrap",
          }}
        >
          {stream.thinking}
        </div>
      )}
      <div
        style={{
          whiteSpace: "pre-wrap",
          color: "var(--text-primary)",
        }}
      >
        {stream.content}
        <span
          style={{
            animation: "blink 0.7s step-end infinite",
          }}
        >
          {"\u2588"}
        </span>
      </div>
    </div>
  );
}
