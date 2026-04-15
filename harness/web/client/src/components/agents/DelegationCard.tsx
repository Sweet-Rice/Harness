import type { DelegationData } from "../../types";
import { useStore } from "../../store";

interface Props {
  data: DelegationData;
}

export function DelegationCard({ data }: Props) {
  const openPopup = useStore((s) => s.openAgentPopup);

  return (
    <div
      onClick={openPopup}
      style={{
        border: "1px solid var(--accent-purple)",
        borderRadius: 4,
        margin: "4px 0",
        background: "var(--bg-input)",
        padding: "8px 12px",
        cursor: "pointer",
        fontSize: "0.85em",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
        }}
      >
        <span
          style={{
            width: 8,
            height: 8,
            borderRadius: "50%",
            background:
              data.status === "running"
                ? "var(--accent-orange)"
                : "var(--accent-green)",
            flexShrink: 0,
          }}
        />
        <span style={{ color: "var(--accent-purple)", fontWeight: "bold" }}>
          agent:{data.agentName}
        </span>
        <span style={{ color: "var(--text-muted)" }}>
          {data.status === "running" ? "running..." : "done"}
        </span>
        <span
          style={{
            marginLeft: "auto",
            color: "var(--text-muted)",
            fontSize: "0.85em",
          }}
        >
          click to inspect {"\u25B6"}
        </span>
      </div>
      <div
        style={{
          color: "var(--text-secondary)",
          marginTop: 4,
          whiteSpace: "nowrap",
          overflow: "hidden",
          textOverflow: "ellipsis",
        }}
      >
        {data.task}
      </div>
      {data.outputPreview && (
        <div
          style={{
            color: "var(--text-muted)",
            marginTop: 4,
            fontSize: "0.85em",
            whiteSpace: "nowrap",
            overflow: "hidden",
            textOverflow: "ellipsis",
          }}
        >
          output: {data.outputPreview}
        </div>
      )}
    </div>
  );
}
