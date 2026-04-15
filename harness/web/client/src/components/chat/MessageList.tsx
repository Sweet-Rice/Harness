import { useStore } from "../../store";
import { useAutoScroll } from "../../hooks/useAutoScroll";
import { UserMessage } from "./UserMessage";
import { AssistantMessage } from "./AssistantMessage";
import { SystemMessage } from "./SystemMessage";
import { LogMessage } from "./LogMessage";
import { StreamingMessage } from "./StreamingMessage";
import { ToolCallCard } from "../tools/ToolCallCard";
import { DelegationCard } from "../agents/DelegationCard";

export function MessageList() {
  const events = useStore((s) => s.events);
  const stream = useStore((s) => s.stream);
  const agentStatus = useStore((s) => s.agentStatus);

  const scrollRef = useAutoScroll([events.length, stream.content]);

  return (
    <div
      ref={scrollRef}
      style={{
        flex: 1,
        overflowY: "auto",
        padding: 16,
        display: "flex",
        flexDirection: "column",
        gap: 4,
      }}
    >
      {events.map((ev, i) => {
        switch (ev.type) {
          case "user":
            return <UserMessage key={i} content={ev.content} />;
          case "assistant":
            return (
              <AssistantMessage
                key={i}
                content={ev.content}
                thinking={ev.thinking}
              />
            );
          case "tool_call":
            return <ToolCallCard key={i} data={ev.data} />;
          case "delegation":
            return <DelegationCard key={i} data={ev.data} />;
          case "system":
            return <SystemMessage key={i} content={ev.content} />;
          case "log":
            return <LogMessage key={i} content={ev.content} />;
          default:
            return null;
        }
      })}

      <StreamingMessage />

      {/* Cooking indicator */}
      {agentStatus !== "idle" && !stream.active && (
        <div
          style={{
            padding: "8px 0",
            fontSize: "0.85em",
            color: "var(--accent-orange)",
          }}
        >
          {agentStatus}
          <span className="dots-anim" />
        </div>
      )}
    </div>
  );
}
