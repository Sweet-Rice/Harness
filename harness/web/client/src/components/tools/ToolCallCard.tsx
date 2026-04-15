import { useState } from "react";
import type { ToolCallData } from "../../types";

interface Props {
  data: ToolCallData;
}

const STATUS_COLORS: Record<string, string> = {
  running: "var(--accent-orange)",
  done: "var(--accent-green)",
  error: "var(--accent-red)",
};

export function ToolCallCard({ data }: Props) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div
      style={{
        border: "1px solid var(--border)",
        borderRadius: 4,
        margin: "4px 0",
        background: "var(--bg-input)",
        fontSize: "0.85em",
      }}
    >
      <div
        onClick={() => setExpanded(!expanded)}
        style={{
          padding: "6px 10px",
          cursor: "pointer",
          display: "flex",
          alignItems: "center",
          gap: 8,
          userSelect: "none",
        }}
      >
        <span
          style={{
            width: 8,
            height: 8,
            borderRadius: "50%",
            background: STATUS_COLORS[data.status] || "var(--text-muted)",
            flexShrink: 0,
          }}
        />
        <span style={{ color: "var(--accent-blue)" }}>{data.name}</span>
        <span style={{ fontSize: "0.7em", color: "var(--text-muted)" }}>
          {expanded ? "\u25BC" : "\u25B6"}
        </span>
        {data.isError && (
          <span style={{ color: "var(--accent-red)", marginLeft: "auto" }}>
            error
          </span>
        )}
      </div>

      {expanded && (
        <div style={{ padding: "0 10px 8px", borderTop: "1px solid var(--border)" }}>
          <div style={{ marginTop: 6 }}>
            <div
              style={{ color: "var(--text-muted)", fontSize: "0.85em", marginBottom: 2 }}
            >
              arguments
            </div>
            <pre
              style={{
                background: "var(--bg-primary)",
                padding: 8,
                borderRadius: 3,
                overflowX: "auto",
                fontSize: "0.9em",
                color: "var(--text-primary)",
              }}
            >
              {JSON.stringify(data.arguments, null, 2)}
            </pre>
          </div>

          {data.result !== undefined && (
            <div style={{ marginTop: 6 }}>
              <div
                style={{
                  color: data.isError ? "var(--accent-red)" : "var(--text-muted)",
                  fontSize: "0.85em",
                  marginBottom: 2,
                }}
              >
                {data.isError ? "error" : "result"}
              </div>
              <ResultDisplay result={data.result} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function ResultDisplay({ result }: { result: string }) {
  const [showFull, setShowFull] = useState(false);
  const isLong = result.length > 500;

  return (
    <div>
      <pre
        style={{
          background: "var(--bg-primary)",
          padding: 8,
          borderRadius: 3,
          overflowX: "auto",
          fontSize: "0.9em",
          color: "var(--text-primary)",
          whiteSpace: "pre-wrap",
          maxHeight: showFull ? "none" : 200,
          overflowY: showFull ? "visible" : "auto",
        }}
      >
        {showFull ? result : result.slice(0, 500)}
        {!showFull && isLong && "..."}
      </pre>
      {isLong && (
        <button
          onClick={() => setShowFull(!showFull)}
          style={{
            background: "none",
            border: "none",
            color: "var(--accent-blue)",
            fontSize: "0.85em",
            cursor: "pointer",
            padding: "2px 0",
            fontFamily: "var(--font-mono)",
          }}
        >
          {showFull ? "show less" : "show all"}
        </button>
      )}
    </div>
  );
}
