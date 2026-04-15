import { useState, useRef, useCallback } from "react";
import { useStore } from "../../store";

export function InputBar() {
  const [text, setText] = useState("");
  const sendMessage = useStore((s) => s.sendMessage);
  const connection = useStore((s) => s.connection);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const send = useCallback(() => {
    const trimmed = text.trim();
    if (!trimmed || connection !== "connected") return;

    // Handle slash commands
    if (trimmed.startsWith("/")) {
      const ws = useStore.getState().ws;
      if (ws && ws.readyState === WebSocket.OPEN) {
        const parts = trimmed.split(/\s+/);
        const cmd = parts[0].slice(1);
        const arg = parts.slice(1).join(" ");

        if (cmd === "new") {
          ws.send(JSON.stringify({ command: "new", name: arg || undefined }));
          useStore.getState().clearEvents();
        } else if (cmd === "list") {
          ws.send(JSON.stringify({ command: "list" }));
        } else if (cmd === "load" && arg) {
          ws.send(JSON.stringify({ command: "load", id: arg }));
          useStore.getState().clearEvents();
        } else if (cmd === "delete" && arg) {
          ws.send(JSON.stringify({ command: "delete", id: arg }));
        } else if (cmd === "rename") {
          const [id, ...rest] = arg.split(/\s+/);
          ws.send(
            JSON.stringify({ command: "rename", id, name: rest.join(" ") })
          );
        } else {
          // Unknown slash command, send as regular message
          sendMessage(trimmed);
        }
      }
    } else {
      sendMessage(trimmed);
    }

    setText("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  }, [text, connection, sendMessage]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setText(e.target.value);
    // Auto-resize
    const ta = e.target;
    ta.style.height = "auto";
    ta.style.height = Math.min(ta.scrollHeight, 200) + "px";
  };

  return (
    <div
      style={{
        display: "flex",
        borderTop: "1px solid var(--border)",
        padding: 12,
        background: "var(--bg-elevated)",
        gap: 8,
        alignItems: "flex-end",
      }}
    >
      <textarea
        ref={textareaRef}
        value={text}
        onChange={handleInput}
        onKeyDown={handleKeyDown}
        placeholder="Task..."
        rows={1}
        style={{
          flex: 1,
          background: "var(--bg-input)",
          border: "1px solid var(--border)",
          color: "var(--text-primary)",
          fontFamily: "var(--font-mono)",
          fontSize: 14,
          padding: "8px 12px",
          outline: "none",
          resize: "none",
          borderRadius: 0,
        }}
        onFocus={(e) =>
          (e.target.style.borderColor = "var(--accent-blue)")
        }
        onBlur={(e) => (e.target.style.borderColor = "var(--border)")}
      />
      <button
        onClick={send}
        style={{
          background: "var(--accent-blue)",
          color: "var(--bg-primary)",
          border: "none",
          padding: "8px 16px",
          fontFamily: "var(--font-mono)",
          fontSize: 14,
          cursor: "pointer",
        }}
        onMouseOver={(e) =>
          (e.currentTarget.style.background = "var(--accent-blue-hover)")
        }
        onMouseOut={(e) =>
          (e.currentTarget.style.background = "var(--accent-blue)")
        }
      >
        Send
      </button>
    </div>
  );
}
