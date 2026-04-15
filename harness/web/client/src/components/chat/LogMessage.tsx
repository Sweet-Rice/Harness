interface Props {
  content: string;
}

export function LogMessage({ content }: Props) {
  return (
    <div
      style={{
        color: "var(--text-muted)",
        fontStyle: "italic",
        fontSize: "0.85em",
        whiteSpace: "pre-wrap",
        padding: "4px 0",
      }}
    >
      {content}
    </div>
  );
}
