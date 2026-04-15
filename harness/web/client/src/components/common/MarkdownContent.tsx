import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface Props {
  content: string;
}

export function MarkdownContent({ content: markdownText }: Props) {
  return (
    <div className="markdown-content">
      <ReactMarkdown
        children={markdownText}
        remarkPlugins={[remarkGfm]}
        components={{
          pre({ children }) {
            return (
              <pre
                style={{
                  background: "var(--bg-input)",
                  padding: 10,
                  borderRadius: 4,
                  overflowX: "auto",
                  margin: "8px 0",
                }}
              >
                {children}
              </pre>
            );
          },
          code({ children, className }) {
            const isBlock = className?.startsWith("language-");
            if (isBlock) {
              return <code>{children}</code>;
            }
            return (
              <code
                style={{
                  background: "var(--bg-input)",
                  padding: "2px 4px",
                  borderRadius: 2,
                  fontSize: "0.9em",
                }}
              >
                {children}
              </code>
            );
          },
        }}
      />
    </div>
  );
}
