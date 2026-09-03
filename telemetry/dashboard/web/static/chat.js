const messagesEl = document.getElementById("messages");
const messagesScrollEl = document.querySelector(".messages-scroll");
const form = document.getElementById("chat-form");
const input = document.getElementById("prompt-input");
const sendBtn = document.getElementById("send-btn");
const newChatBtn = document.getElementById("new-chat-btn");

const MAX_HISTORY_MESSAGES = 30;
let chatHistory = [];
let chatSessionId = crypto.randomUUID();

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text ?? "";
  return div.innerHTML;
}

function scrollToBottom() {
  if (messagesScrollEl) {
    messagesScrollEl.scrollTop = messagesScrollEl.scrollHeight;
  }
}

function appendMessage(className, html) {
  const el = document.createElement("div");
  el.className = `msg ${className}`;
  el.innerHTML = html;
  messagesEl.appendChild(el);
  scrollToBottom();
  return el;
}

function formatDetails(data) {
  const lines = [
    `reason: ${data.reason}`,
    `complexity_score: ${data.complexity_score}`,
    `latency_ms: ${data.latency_ms}`,
    `model: ${data.model}`,
    `request_id: ${data.request_id}`,
  ];
  if (data.sensitivity_flag && data.sensitivity_triggers?.length) {
    lines.push(`sensitivity_triggers:`);
    data.sensitivity_triggers.forEach((t) => lines.push(`  - ${t}`));
  }
  if (data.mock_execution) {
    lines.push(`note: mock execution (configure GGUF models or OPENAI_API_KEY)`);
  }
  return lines.join("\n");
}

function renderAssistantMessage(data) {
  const sensClass = data.sensitivity_flag ? "on" : "";
  const sensLabel = data.sensitivity_flag ? "sensitive" : "not sensitive";
  const truncated = data.finish_reason === "length";
  return `
    <p class="msg-body">${escapeHtml(data.text)}</p>
    <div class="msg-meta">
      <span class="target-badge ${escapeHtml(data.target)}">${escapeHtml(data.target)}</span>
      <span class="sens-badge ${sensClass}">${sensLabel}</span>
      ${truncated ? '<span class="sens-badge on">truncated at token limit</span>' : ""}
      <span class="sens-badge">${data.latency_ms} ms</span>
    </div>
    <details class="route-details">
      <summary>routing details</summary>
      <pre>${escapeHtml(formatDetails(data))}</pre>
    </details>
  `;
}

function setLoading(loading) {
  input.disabled = loading;
  sendBtn.disabled = loading;
  sendBtn.textContent = loading ? "working…" : "send";
  sendBtn.classList.toggle("is-busy", loading);
}

function formatElapsed(seconds) {
  if (seconds < 60) return `${seconds}s`;
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}m ${s}s`;
}

function thinkingMessage(elapsedSec) {
  if (elapsedSec < 3) {
    return "Checking sensitivity and routing…";
  }
  if (elapsedSec < 10) {
    return "Running inference — local models can take a while…";
  }
  return `Still working — large_local / 7B prompts often take 15–30s (${formatElapsed(elapsedSec)})`;
}

function showThinkingIndicator() {
  const el = appendMessage(
    "thinking",
    `
    <div class="thinking-row">
      <span class="thinking-pulse" aria-hidden="true"></span>
      <div class="thinking-copy">
        <p class="thinking-title">Thinking</p>
        <p class="thinking-status" data-thinking-status>Checking sensitivity and routing…</p>
        <p class="thinking-elapsed" data-thinking-elapsed>0s</p>
      </div>
    </div>
    `
  );
  el.setAttribute("aria-busy", "true");
  el.setAttribute("aria-label", "Assistant is thinking");

  const statusEl = el.querySelector("[data-thinking-status]");
  const elapsedEl = el.querySelector("[data-thinking-elapsed]");
  const started = Date.now();

  const timer = window.setInterval(() => {
    const elapsedSec = Math.floor((Date.now() - started) / 1000);
    if (statusEl) statusEl.textContent = thinkingMessage(elapsedSec);
    if (elapsedEl) elapsedEl.textContent = formatElapsed(elapsedSec);
  }, 1000);

  return {
    remove() {
      window.clearInterval(timer);
      el.remove();
    },
  };
}

async function consumeChatStream(response, bodyEl) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let doneData = null;

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() || "";
    for (const part of parts) {
      const line = part.trim();
      if (!line.startsWith("data: ")) continue;
      const event = JSON.parse(line.slice(6));
      if (event.type === "token") {
        bodyEl.textContent += event.text;
        scrollToBottom();
      } else if (event.type === "done") {
        doneData = event;
      } else if (event.type === "error") {
        throw new Error(event.detail || event.error || "Inference failed");
      }
    }
  }

  if (!doneData) {
    throw new Error("Stream ended before completion");
  }
  return doneData;
}

async function sendMessage(prompt) {
  appendMessage("user", `<p class="msg-body">${escapeHtml(prompt)}</p>`);
  chatHistory.push({ role: "user", content: prompt });
  if (chatHistory.length > MAX_HISTORY_MESSAGES) {
    chatHistory = chatHistory.slice(-MAX_HISTORY_MESSAGES);
  }

  const thinking = showThinkingIndicator();
  setLoading(true);

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        messages: chatHistory,
        session_id: chatSessionId,
        stream: true,
      }),
    });

    thinking.remove();

    if (!res.ok) {
      chatHistory.pop();
      const data = await res.json().catch(() => ({}));
      const detail = data.detail || data.error || res.statusText;
      appendMessage(
        "error",
        `<p class="msg-body"><strong>${escapeHtml(data.error || "Request failed")}</strong>\n${escapeHtml(detail)}</p>`
      );
      return;
    }

    const assistant = appendMessage(
      "assistant",
      '<p class="msg-body" data-stream-body></p>'
    );
    const bodyEl = assistant.querySelector("[data-stream-body]");
    const doneData = await consumeChatStream(res, bodyEl);

    assistant.innerHTML = renderAssistantMessage(doneData);
    chatHistory.push({ role: "assistant", content: doneData.text });
    if (chatHistory.length > MAX_HISTORY_MESSAGES) {
      chatHistory = chatHistory.slice(-MAX_HISTORY_MESSAGES);
    }
    scrollToBottom();
  } catch (err) {
    thinking.remove();
    chatHistory.pop();
    appendMessage(
      "error",
      `<p class="msg-body">Network error: ${escapeHtml(err.message)}</p>`
    );
  } finally {
    setLoading(false);
    input.focus();
  }
}

function resetChat() {
  const previousSession = chatSessionId;
  chatHistory = [];
  chatSessionId = crypto.randomUUID();
  messagesEl.innerHTML = "";
  fetch("/api/chat/new", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: previousSession }),
  }).catch(() => {});
  input.focus();
}

form.addEventListener("submit", (e) => {
  e.preventDefault();
  const prompt = input.value.trim();
  if (!prompt) return;
  input.value = "";
  sendMessage(prompt);
});

if (newChatBtn) {
  newChatBtn.addEventListener("click", resetChat);
}

input.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    form.requestSubmit();
  }
});

input.focus();
