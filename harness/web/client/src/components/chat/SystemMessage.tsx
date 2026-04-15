interface Props {
  content: string;
}

export function SystemMessage({ content }: Props) {
  return (
    <div
      style={{
        color: "var(--accent-orange)",
        fontSize: "0.85em",
        fontStyle: "italic",
        padding: "6px 0",
      }}
    >
      {content}
    </div>
  );
}
