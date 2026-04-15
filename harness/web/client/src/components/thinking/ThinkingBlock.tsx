import { Collapsible } from "../common/Collapsible";

interface Props {
  content: string;
}

export function ThinkingBlock({ content }: Props) {
  return (
    <Collapsible label="thinking" labelColor="var(--accent-purple)">
      <div
        style={{
          color: "var(--accent-purple)",
          fontSize: "0.85em",
          fontStyle: "italic",
          whiteSpace: "pre-wrap",
          borderLeft: "2px solid var(--accent-purple)",
          paddingLeft: 8,
          maxHeight: 300,
          overflowY: "auto",
        }}
      >
        {content}
      </div>
    </Collapsible>
  );
}
