import { ConversationSidebar } from "./sidebar/ConversationSidebar";
import { StatusBar } from "./chat/StatusBar";
import { MessageList } from "./chat/MessageList";
import { InputBar } from "./chat/InputBar";
import { ContextPanel } from "./context/ContextPanel";
import { AgentPopup } from "./agents/AgentPopup";

export function Layout() {
  return (
    <>
      <div
        style={{
          display: "flex",
          height: "100vh",
          overflow: "hidden",
        }}
      >
        <ConversationSidebar />

        <div
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            minWidth: 0,
          }}
        >
          <StatusBar />
          <MessageList />
          <InputBar />
        </div>

        <ContextPanel />
      </div>

      <AgentPopup />
    </>
  );
}
