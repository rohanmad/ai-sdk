const messagesEl = document.getElementById("messages");
const form = document.getElementById("chat-form");
const input = document.getElementById("prompt-input");
const sendBtn = document.getElementById("send-btn");

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text ?? "";
  return div.innerHTML;
}

function scrollToBottom() {
  messagesEl.scrollTop = messagesEl.scrollHeight;
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
  return `
    <p class="msg-body">${escapeHtml(data.text)}</p>
    <div class="msg-meta">
      <span class="target-badge ${escapeHtml(data.target)}">${escapeHtml(data.target)}</span>
      <span class="sens-badge ${sensClass}">${sensLabel}</span>
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
}

async function sendMessage(prompt) {
  appendMessage("user", `<p class="msg-body">${escapeHtml(prompt)}</p>`);
  const thinking = appendMessage("thinking", `<p class="msg-body">routing…</p>`);
  setLoading(true);

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt, max_tokens: 256 }),
    });
    const data = await res.json();
    thinking.remove();

    if (!res.ok) {
      const detail = data.detail || data.error || res.statusText;
      appendMessage(
        "error",
        `<p class="msg-body"><strong>${escapeHtml(data.error || "Request failed")}</strong>\n${escapeHtml(detail)}</p>`
      );
      return;
    }

    const assistant = appendMessage("assistant", "");
    assistant.innerHTML = renderAssistantMessage(data);
    scrollToBottom();
  } catch (err) {
    thinking.remove();
    appendMessage(
      "error",
      `<p class="msg-body">Network error: ${escapeHtml(err.message)}</p>`
    );
  } finally {
    setLoading(false);
    input.focus();
  }
}

form.addEventListener("submit", (e) => {
  e.preventDefault();
  const prompt = input.value.trim();
  if (!prompt) return;
  input.value = "";
  sendMessage(prompt);
});

input.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    form.requestSubmit();
  }
});

input.focus();
