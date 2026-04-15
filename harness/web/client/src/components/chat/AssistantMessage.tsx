import { MarkdownContent } from "../common/MarkdownContent";
import { ThinkingBlock } from "../thinking/ThinkingBlock";

interface Props {
  content: string;
  thinking?: string;
}

export function AssistantMessage({ content, thinking }: Props) {
  return (
    <div style={{ padding: "6px 0", wordWrap: "break-word" }}>
      {thinking && <ThinkingBlock content={thinking} />}
      <MarkdownContent content={content} />
    </div>
  );
}
