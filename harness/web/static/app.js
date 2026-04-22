marked.setOptions({ breaks: true });

const messagesEl = document.getElementById("messages");
const inputEl = document.getElementById("input");
const sendEl = document.getElementById("send");
const convoListEl = document.getElementById("convo-list");
const newChatEl = document.getElementById("new-chat");
const refreshListEl = document.getElementById("refresh-list");
const statusChipEl = document.getElementById("status-chip");
const cookingChipEl = document.getElementById("cooking-chip");
const sidebarEl = document.getElementById("sidebar");
const inspectorEl = document.getElementById("inspector");
const backdropEl = document.getElementById("panel-backdrop");
const sidebarToggleEl = document.getElementById("sidebar-toggle");
const inspectorToggleEl = document.getElementById("inspector-toggle");
const sidebarCloseEl = document.getElementById("sidebar-close");
const inspectorCloseEl = document.getElementById("inspector-close");
const paletteEl = document.getElementById("slash-palette");
const paletteListEl = document.getElementById("palette-list");
const panelThinkingEl = document.getElementById("panel-thinking");
const panelDelegatesEl = document.getElementById("panel-delegates");
const panelPlanEl = document.getElementById("panel-plan");
const panelLogsEl = document.getElementById("panel-logs");
const tabButtons = Array.from(document.querySelectorAll(".tab-btn"));
const tabPanels = {
  thinking: panelThinkingEl,
  delegates: panelDelegatesEl,
  plan: panelPlanEl,
  logs: panelLogsEl,
};

let ws;
let runtimeConfig = null;
let streamDiv = null;
let streamContent = "";
let lastStreamFinalContent = "";
let paletteItems = [];
let filteredPaletteItems = [];
let paletteIndex = 0;

const traceState = {
  mainThinking: "",
  delegates: new Map(),
  plan: null,
  logs: [],
  toolEvents: [],
};

function pushLimited(target, value, limit = 80) {
  target.push(value);
  if (target.length > limit) {
    target.splice(0, target.length - limit);
  }
}

function resetTraceState(reason = "Trace resets when the page reloads or the websocket reconnects.") {
  traceState.mainThinking = "";
  traceState.delegates = new Map();
  traceState.plan = null;
  traceState.logs = [];
  traceState.toolEvents = [];
  renderInspector(reason);
}

async function loadRuntimeConfig() {
  if (runtimeConfig) {
    return runtimeConfig;
  }
  const response = await fetch("/runtime-config.json");
  runtimeConfig = await response.json();
  paletteItems = [...(runtimeConfig.commands || []), ...(runtimeConfig.skills || [])];
  return runtimeConfig;
}

function setSocketStatus(text, tone) {
  statusChipEl.innerHTML = `<strong>Socket</strong> ${text}`;
  statusChipEl.classList.toggle("live", tone === "ok");
  statusChipEl.style.color = tone === "error" ? "var(--danger)" : "";
}

function setCookingStatus(label) {
  cookingChipEl.innerHTML = `<strong>State</strong> ${label}`;
}

function syncPanelBackdrop() {
  const sidebarNeedsBackdrop = window.innerWidth <= 900 && sidebarEl.classList.contains("open");
  const tabletDrawerMode = window.innerWidth <= 1260;
  const inspectorNeedsBackdrop = tabletDrawerMode && inspectorEl.classList.contains("open");
  const tabletSidebarNeedsBackdrop = tabletDrawerMode && sidebarEl.classList.contains("open");
  backdropEl.classList.toggle("open", sidebarNeedsBackdrop || inspectorNeedsBackdrop || tabletSidebarNeedsBackdrop);
}

function syncResponsivePanels() {
  if (window.innerWidth > 1260) {
    sidebarEl.classList.remove("open");
    inspectorEl.classList.remove("open");
  }
  syncPanelBackdrop();
}

function closeSidebar() {
  sidebarEl.classList.remove("open");
  syncPanelBackdrop();
}

function closeInspector() {
  inspectorEl.classList.remove("open");
  syncPanelBackdrop();
}

function addChatMessage(type, content) {
  const div = document.createElement("div");
  div.className = `msg ${type}`;

  if (type === "message") {
    div.innerHTML = marked.parse(content);
  } else {
    div.textContent = content;
  }

  messagesEl.appendChild(div);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return div;
}

function beginStream() {
  streamContent = "";
  streamDiv = addChatMessage("message", "");
  streamDiv.classList.add("streaming");
  streamDiv.textContent = "";
}

function appendStream(content) {
  if (!streamDiv) {
    return;
  }
  streamContent += content;
  streamDiv.textContent = streamContent;
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function endStream() {
  if (!streamDiv) {
    return;
  }
  const finalContent = streamContent.trim();
  if (finalContent) {
    streamDiv.innerHTML = marked.parse(streamContent);
    streamDiv.classList.remove("streaming");
    lastStreamFinalContent = streamContent;
  } else {
    streamDiv.remove();
  }
  streamDiv = null;
  streamContent = "";
}

function renderConversations(convos, currentId) {
  convoListEl.innerHTML = "";
  convos.forEach((convo) => {
    const item = document.createElement("div");
    item.className = `convo-item${convo.id === currentId ? " active" : ""}`;

    const main = document.createElement("div");
    main.className = "convo-main";
    main.innerHTML = `
      <div class="convo-name">${convo.name}</div>
      <div class="convo-meta mono">${convo.message_count} msgs • ${convo.mode}</div>
    `;
    main.addEventListener("click", () => {
      messagesEl.innerHTML = "";
      resetTraceState("Loaded a different conversation. Detailed trace remains session-only.");
      ws.send(JSON.stringify({ command: "load", id: convo.id }));
      if (window.innerWidth <= 900) {
        closeSidebar();
      }
    });

    const delBtn = document.createElement("button");
    delBtn.className = "delete-btn icon-btn";
    delBtn.textContent = "×";
    delBtn.addEventListener("click", (event) => {
      event.stopPropagation();
      ws.send(JSON.stringify({ command: "delete", id: convo.id }));
    });

    item.appendChild(main);
    item.appendChild(delBtn);
    convoListEl.appendChild(item);
  });
}

function upsertDelegateTrace(payload = {}) {
  const key = payload.step_id || payload.title || "delegate";
  const existing = traceState.delegates.get(key) || {
    step_id: payload.step_id || "",
    title: payload.title || "Delegated step",
    status: "idle",
    thinking: "",
    events: [],
    finalContent: "",
  };

  existing.step_id = payload.step_id || existing.step_id;
  existing.title = payload.title || existing.title;
  if (payload.status) {
    existing.status = payload.status;
  }
  if (payload.content) {
    existing.finalContent = payload.content;
  }
  existing.events.push({
    status: payload.status || "update",
    content: payload.content || "",
    timestamp: new Date().toLocaleTimeString(),
  });
  traceState.delegates.set(key, existing);
}

function appendDelegateThinking(payload = {}) {
  const key = payload.step_id || payload.title || "delegate";
  const existing = traceState.delegates.get(key) || {
    step_id: payload.step_id || "",
    title: payload.title || "Delegated step",
    status: "thinking",
    thinking: "",
    events: [],
    finalContent: "",
  };

  existing.step_id = payload.step_id || existing.step_id;
  existing.title = payload.title || existing.title;
  existing.status = "thinking";
  existing.thinking += payload.content || "";
  traceState.delegates.set(key, existing);
}

function renderThinkingPanel(reasonText) {
  const content = traceState.mainThinking.trim();
  panelThinkingEl.innerHTML = "";
  if (!content) {
    panelThinkingEl.innerHTML = `<div class="empty-state">${reasonText || "Main-agent thinking will appear here when the provider exposes it."}</div>`;
    return;
  }

  const card = document.createElement("div");
  card.className = "trace-card";
  card.innerHTML = `
    <div class="trace-title">Main agent thought stream</div>
    <div class="trace-meta">Session-only raw reasoning</div>
    <div class="trace-content mono">${escapeHtml(content)}</div>
  `;
  panelThinkingEl.appendChild(card);
}

function renderDelegatesPanel(reasonText) {
  panelDelegatesEl.innerHTML = "";
  const entries = Array.from(traceState.delegates.values());
  if (!entries.length) {
    panelDelegatesEl.innerHTML = `<div class="empty-state">${reasonText || "Delegated step traces will appear here when the orchestrator spins up sub-agents."}</div>`;
    return;
  }

  entries.forEach((entry) => {
    const card = document.createElement("div");
    card.className = "trace-card";
    const statusClass =
      entry.status === "failed" ? "danger" : entry.status === "blocked" ? "warning" : "";
    const eventsMarkup = entry.events
      .slice(-4)
      .map(
        (event) =>
          `<div class="trace-meta">${event.timestamp} • ${escapeHtml(event.status)}${event.content ? ` — ${escapeHtml(event.content)}` : ""}</div>`,
      )
      .join("");
    card.innerHTML = `
      <div class="trace-head">
        <div class="trace-title">${escapeHtml(entry.title)}</div>
        <span class="trace-pill ${statusClass}">${escapeHtml(entry.status)}</span>
      </div>
      ${entry.step_id ? `<div class="trace-meta mono">step ${escapeHtml(entry.step_id)}</div>` : ""}
      ${entry.thinking ? `<div class="trace-content mono">${escapeHtml(entry.thinking)}</div>` : ""}
      ${entry.finalContent ? `<div class="trace-content">${escapeHtml(entry.finalContent)}</div>` : ""}
      ${eventsMarkup}
    `;
    panelDelegatesEl.appendChild(card);
  });
}

function renderPlanPanel(reasonText) {
  panelPlanEl.innerHTML = "";
  if (!traceState.plan) {
    panelPlanEl.innerHTML = `<div class="empty-state">${reasonText || "Canonical plan updates will appear here during orchestrated web runs."}</div>`;
    return;
  }

  const plan = traceState.plan;
  const wrapper = document.createElement("div");
  wrapper.className = "trace-card";
  wrapper.innerHTML = `
    <div class="trace-title">${escapeHtml(plan.title || "Current plan")}</div>
    <div class="trace-meta">${escapeHtml(plan.overall_status || "unknown")}</div>
    <div class="trace-content">${escapeHtml(plan.objective || "No objective")}</div>
  `;
  panelPlanEl.appendChild(wrapper);

  const stepsWrap = document.createElement("div");
  stepsWrap.className = "steps-list";
  (plan.steps || []).forEach((step) => {
    const row = document.createElement("div");
    row.className = `step-row${step.step_id === plan.active_step_id ? " active" : ""}`;
    const statusClass = step.status === "failed" ? "danger" : step.status === "blocked" ? "warning" : "";
    row.innerHTML = `
      <div class="step-top">
        <div class="step-title">${escapeHtml(step.title)}</div>
        <span class="trace-pill ${statusClass}">${escapeHtml(step.status)}</span>
      </div>
      <div class="trace-meta mono">${escapeHtml(step.step_id)} • ${escapeHtml(step.owner)}</div>
      ${step.latest_note ? `<div class="step-note">${escapeHtml(step.latest_note)}</div>` : ""}
    `;
    stepsWrap.appendChild(row);
  });
  panelPlanEl.appendChild(stepsWrap);

  if ((plan.recent_notes || []).length) {
    const notes = document.createElement("div");
    notes.className = "trace-card";
    notes.innerHTML = `
      <div class="trace-title">Recent plan notes</div>
      <div class="trace-content">${plan.recent_notes.map((note) => `• ${escapeHtml(note)}`).join("<br>")}</div>
    `;
    panelPlanEl.appendChild(notes);
  }
}

function renderLogsPanel(reasonText) {
  panelLogsEl.innerHTML = "";
  const entries = [
    ...traceState.toolEvents.map((event) => ({ kind: "tool", ...event })),
    ...traceState.logs.map((event) => ({ kind: "log", ...event })),
  ];
  if (!entries.length) {
    panelLogsEl.innerHTML = `<div class="empty-state">${reasonText || "Tool events, warnings, and diagnostics will gather here."}</div>`;
    return;
  }

  entries
    .slice(-20)
    .reverse()
    .forEach((entry) => {
      const card = document.createElement("div");
      card.className = "trace-card";
      const label = entry.kind === "tool" ? "Tool event" : "Diagnostic log";
      card.innerHTML = `
        <div class="trace-title">${label}</div>
        <div class="trace-meta">${escapeHtml(entry.timestamp || "")}</div>
        <div class="trace-content mono">${escapeHtml(entry.content || entry.summary || JSON.stringify(entry, null, 2))}</div>
      `;
      panelLogsEl.appendChild(card);
    });
}

function renderInspector(reasonText = "") {
  renderThinkingPanel(reasonText);
  renderDelegatesPanel(reasonText);
  renderPlanPanel(reasonText);
  renderLogsPanel(reasonText);
}

function setActiveTab(tabName) {
  tabButtons.forEach((button) => {
    button.classList.toggle("active", button.dataset.tab === tabName);
  });
  Object.entries(tabPanels).forEach(([name, panel]) => {
    panel.classList.toggle("active", name === tabName);
  });
}

function escapeHtml(text) {
  return String(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function updatePalette() {
  const text = inputEl.value;
  const slashIndex = text.lastIndexOf("/");
  const shouldOpen = slashIndex >= 0 && (slashIndex === 0 || /\s/.test(text[slashIndex - 1]));
  if (!shouldOpen) {
    closePalette();
    return;
  }

  const query = text.slice(slashIndex + 1).trim().replace(/^skill\s+/, "").toLowerCase();
  filteredPaletteItems = paletteItems.filter((item) => {
    const haystack = `${item.name} ${item.description || ""} ${item.scaffold || ""}`.toLowerCase();
    return haystack.includes(query);
  });

  if (!filteredPaletteItems.length) {
    closePalette();
    return;
  }

  paletteIndex = Math.min(paletteIndex, filteredPaletteItems.length - 1);
  paletteEl.classList.add("open");
  paletteListEl.innerHTML = "";

  filteredPaletteItems.forEach((item, index) => {
    const option = document.createElement("div");
    option.className = `palette-item${index === paletteIndex ? " active" : ""}`;
    option.innerHTML = `
      <div>
        <div class="palette-name">${escapeHtml(item.name)}</div>
      </div>
      <span class="palette-type">${escapeHtml(item.type || "item")}</span>
    `;
    option.addEventListener("mousedown", (event) => {
      event.preventDefault();
      applyPaletteItem(index);
    });
    paletteListEl.appendChild(option);
  });
}

function closePalette() {
  paletteEl.classList.remove("open");
  filteredPaletteItems = [];
  paletteIndex = 0;
}

function applyPaletteItem(index) {
  const item = filteredPaletteItems[index];
  if (!item) {
    return;
  }
  inputEl.value = item.scaffold || item.name;
  closePalette();
  inputEl.focus();
}

function handleTraceEvent(type, payload) {
  if (type === "trace.main_thinking") {
    traceState.mainThinking += payload.content || "";
    renderThinkingPanel();
    return;
  }

  if (type === "trace.subagent_thinking") {
    appendDelegateThinking(payload);
    renderDelegatesPanel();
    return;
  }

  if (type === "trace.subagent_status") {
    upsertDelegateTrace(payload);
    renderDelegatesPanel();
    return;
  }

  if (type === "trace.plan_update") {
    traceState.plan = payload;
    renderPlanPanel();
    return;
  }

  if (type === "trace.tool_event") {
    pushLimited(traceState.toolEvents, {
      timestamp: new Date().toLocaleTimeString(),
      content: `${payload.name} • ${payload.status}${payload.error ? ` • ${payload.error}` : ""}${payload.result_preview ? ` • ${payload.result_preview}` : ""}`,
      summary: payload.status,
    });
    renderLogsPanel();
    return;
  }

  if (type === "trace.log") {
    pushLimited(traceState.logs, {
      timestamp: new Date().toLocaleTimeString(),
      content: payload.content || "",
    });
    renderLogsPanel();
  }
}

async function connect() {
  const config = await loadRuntimeConfig();
  ws = new WebSocket(config.ws_url);
  resetTraceState("Deep trace is live-only and resets when the session reconnects.");

  ws.onopen = () => {
    setSocketStatus("connected", "ok");
  };

  ws.onclose = () => {
    setSocketStatus("disconnected — reconnecting", "error");
    setCookingStatus("idle");
    resetTraceState("Connection dropped. Live trace will resume after reconnect, but prior deep reasoning is session-only.");
    setTimeout(() => {
      connect();
    }, 2000);
  };

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);

    if (data.type === "status") {
      setCookingStatus(data.content);
      return;
    }

    if (data.type === "conversations") {
      renderConversations(data.content, data.current);
      return;
    }

    if (data.type.startsWith("trace.")) {
      handleTraceEvent(data.type, data.content || {});
      return;
    }

    if (data.type === "stream_start") {
      beginStream();
      return;
    }

    if (data.type === "stream_token") {
      appendStream(data.content);
      return;
    }

    if (data.type === "stream_end") {
      endStream();
      return;
    }

    if (data.type === "message") {
      if (lastStreamFinalContent && data.content === lastStreamFinalContent) {
        lastStreamFinalContent = "";
        return;
      }
      addChatMessage("message", data.content);
      return;
    }

    addChatMessage(data.type, data.content);
  };
}

function send() {
  const text = inputEl.value.trim();
  if (!text || !ws || ws.readyState !== WebSocket.OPEN) {
    return;
  }

  addChatMessage("user", text);
  ws.send(JSON.stringify({ content: text }));
  inputEl.value = "";
  closePalette();
}

newChatEl.addEventListener("click", () => {
  messagesEl.innerHTML = "";
  resetTraceState("Started a fresh conversation. Live trace is tied to the current session only.");
  ws.send(JSON.stringify({ command: "new" }));
  sidebarEl.classList.remove("open");
  syncPanelBackdrop();
});

refreshListEl.addEventListener("click", () => {
  ws.send(JSON.stringify({ command: "list" }));
});

sendEl.addEventListener("click", send);

inputEl.addEventListener("input", updatePalette);
inputEl.addEventListener("keydown", (event) => {
  if (paletteEl.classList.contains("open")) {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      paletteIndex = (paletteIndex + 1) % filteredPaletteItems.length;
      updatePalette();
      return;
    }
    if (event.key === "ArrowUp") {
      event.preventDefault();
      paletteIndex = (paletteIndex - 1 + filteredPaletteItems.length) % filteredPaletteItems.length;
      updatePalette();
      return;
    }
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      applyPaletteItem(paletteIndex);
      return;
    }
    if (event.key === "Escape") {
      closePalette();
      return;
    }
  }

  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    send();
  }
});

document.addEventListener("click", (event) => {
  if (!paletteEl.contains(event.target) && event.target !== inputEl) {
    closePalette();
  }
});

tabButtons.forEach((button) => {
  button.addEventListener("click", () => setActiveTab(button.dataset.tab));
});

sidebarToggleEl.addEventListener("click", () => {
  sidebarEl.classList.toggle("open");
  syncPanelBackdrop();
});

inspectorToggleEl.addEventListener("click", () => {
  inspectorEl.classList.toggle("open");
  syncPanelBackdrop();
});

sidebarCloseEl.addEventListener("click", closeSidebar);
inspectorCloseEl.addEventListener("click", closeInspector);
backdropEl.addEventListener("click", () => {
  closeSidebar();
  closeInspector();
});

window.addEventListener("resize", syncResponsivePanels);
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    closeSidebar();
    closeInspector();
    closePalette();
  }
});

syncResponsivePanels();
connect();
