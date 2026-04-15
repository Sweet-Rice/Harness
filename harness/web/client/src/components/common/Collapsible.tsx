import { useState, type ReactNode } from "react";

interface Props {
  label: string;
  defaultOpen?: boolean;
  labelColor?: string;
  children: ReactNode;
}

export function Collapsible({
  label,
  defaultOpen = false,
  labelColor,
  children,
}: Props) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div style={{ marginBottom: 4 }}>
      <div
        onClick={() => setOpen(!open)}
        style={{
          cursor: "pointer",
          userSelect: "none",
          fontSize: "0.85em",
          color: labelColor || "var(--text-muted)",
          display: "flex",
          alignItems: "center",
          gap: 4,
        }}
      >
        <span style={{ fontSize: "0.7em" }}>{open ? "\u25BC" : "\u25B6"}</span>
        {label}
      </div>
      {open && <div style={{ marginTop: 4 }}>{children}</div>}
    </div>
  );
}
