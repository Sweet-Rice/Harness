interface Props {
  content: string;
}

export function UserMessage({ content }: Props) {
  return (
    <div
      style={{
        color: "var(--accent-blue)",
        whiteSpace: "pre-wrap",
        padding: "6px 0",
        wordWrap: "break-word",
      }}
    >
      <span style={{ opacity: 0.6 }}>&gt; </span>
      {content}
    </div>
  );
}
