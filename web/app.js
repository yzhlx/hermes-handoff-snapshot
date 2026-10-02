/* Cloud Hermes web client (Track C). Same-origin deploy: API base is "". Uses Bearer token
   (Authorization header) so CSRF is not required. No long-lived token in localStorage. */
(function () {
  "use strict";

  const state = {
    token: sessionStorage.getItem("hermes_token") || null,
    csrf: null,
    deviceId: sessionStorage.getItem("hermes_device") || (function () {
      const d = "web_" + crypto.randomUUID().slice(0, 12);
      sessionStorage.setItem("hermes_device", d);
      return d;
    })(),
    conversationId: null,
  };

  const $ = (sel) => document.querySelector(sel);
  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  const ERROR_TEXT = {
    HERMES_UNAVAILABLE: "云端 Hermes 暂时不可用，请稍后重试。",
    AUTH_REQUIRED: "请先登录。",
    AUTH_EXPIRED: "登录已过期，请重新登录。",
    AUTH_INVALID: "用户名或密码错误。",
    PROVIDER_UNAVAILABLE: "AI 服务暂时不可用。",
    PROVIDER_TIMEOUT: "AI 服务响应超时。",
    PROVIDER_INVALID_RESPONSE: "AI 服务返回异常。",
    MEMORY_UNAVAILABLE: "记忆服务暂时不可用。",
    WRITEBACK_FAILED: "结果写入失败，但对话已完成。",
    RATE_LIMITED: "操作过于频繁，请稍后再试。",
    REQUEST_TIMEOUT: "请求超时。",
    INVALID_RESPONSE: "响应格式异常。",
    LOCAL_EXECUTION_PENDING: "命令已加入本地队列，等待电脑上线执行。",
    VALIDATION_ERROR: "请求参数有误。",
    CONFLICT: "请求冲突。",
    NOT_FOUND: "未找到对应资源。",
    INTERNAL_ERROR: "服务器内部错误。",
  };
  function errText(code) { return ERROR_TEXT[code] || "发生未知错误。"; }

  function banner(msg, kind) {
    const b = $("#banner");
    b.textContent = msg;
    b.className = "banner" + (kind ? " " + kind : "");
    b.hidden = false;
    clearTimeout(banner._t);
    banner._t = setTimeout(() => { b.hidden = true; }, 5000);
  }

  async function api(path, opts) {
    opts = opts || {};
    const headers = Object.assign({ "Content-Type": "application/json" }, opts.headers || {});
    if (state.token) headers["Authorization"] = "Bearer " + state.token;
    headers["X-Device-Id"] = state.deviceId;
    if (opts.idempotencyKey) headers["Idempotency-Key"] = opts.idempotencyKey;
    const res = await fetch(path, { method: opts.method || "GET", headers, body: opts.body ? JSON.stringify(opts.body) : undefined });
    let data = null;
    try { data = await res.json(); } catch (e) { data = {}; }
    if (!res.ok) {
      const code = (data && data.code) || "INTERNAL_ERROR";
      const err = new Error(data && data.error ? data.error : errText(code));
      err.code = code; err.status = res.status;
      throw err;
    }
    return data;
  }

  async function refreshStatus() {
    const el = $("#connStatus");
    try {
      const h = await api("/api/hermes/v1/health");
      el.textContent = "云端在线" + (h.provider_configured ? "" : "（未配置 Provider）");
      el.className = "status on";
      if (state.token) {
        const n = await api("/api/hermes/v1/execution-nodes");
        $("#nodeStatus").textContent = n.status === "online" ? "本地节点：在线" : "本地节点：离线（云端对话正常）";
        $("#nodeStatus").style.color = n.status === "online" ? "var(--ok)" : "var(--warn)";
      }
    } catch (e) {
      el.textContent = "云端不可达";
      el.className = "status off";
    }
  }

  function showLogin(show) { $("#loginModal").hidden = !show; }

  async function doLogin(username, password) {
    const r = await api("/api/hermes/v1/auth/login", { method: "POST", body: { username, password } });
    state.token = r.access_token; state.csrf = r.csrf_token;
    sessionStorage.setItem("hermes_token", state.token);
    $("#logoutBtn").hidden = false;
    showLogin(false);
    await refreshStatus(); await loadConversations(); await loadTasks();
  }

  function renderMessage(role, content, basis) {
    const div = document.createElement("article");
    div.className = "msg " + (role === "user" ? "user" : "");
    const html = `<div class="role">${role === "user" ? "你" : "Hermes"}</div><p>${escapeHtml(content)}</p>`;
    div.innerHTML = html;
    if (basis) {
      const d = document.createElement("details");
      d.className = "basis";
      d.innerHTML = `<summary>本轮依据</summary>
        Hermes Run：<code>${escapeHtml(basis.hermes_run_id)}</code><br>
        检索记忆：${basis.memory_refs} 条 · 写入事件：${basis.event_ids} 条<br>
        ${basis.warnings && basis.warnings.length ? "警告：" + escapeHtml(basis.warnings.join("，")) : ""}`;
      div.appendChild(d);
    }
    $("#messages").appendChild(div);
    $("#messages").scrollTop = $("#messages").scrollHeight;
  }

  async function sendMessage(text) {
    if (!state.token) { showLogin(true); return; }
    renderMessage("user", text);
    const idem = crypto.randomUUID();
    try {
      const r = await api("/api/hermes/v1/chat", {
        method: "POST", idempotencyKey: idem,
        body: { conversation_id: state.conversationId, role_id: "master", message: text,
                client: { type: "web", device_id: state.deviceId, client_version: "v1" } },
      });
      state.conversationId = r.conversation_id;
      renderMessage("assistant", r.reply, {
        hermes_run_id: r.hermes_run_id, memory_refs: (r.memory_refs || []).length,
        event_ids: (r.event_ids || []).length, warnings: r.warnings || [],
      });
      await loadConversations();
    } catch (e) {
      banner((e.code ? "[" + e.code + "] " : "") + (e.message || errText(e.code)), e.code === "LOCAL_EXECUTION_PENDING" ? "warn" : "err");
    }
  }

  async function loadConversations() {
    if (!state.token) return;
    const r = await api("/api/hermes/v1/conversations");
    const list = $("#chatList"); list.innerHTML = "";
    (r.items || []).forEach((c) => {
      const li = document.createElement("li");
      li.textContent = c.title || "新对话";
      li.onclick = () => openConversation(c.id);
      list.appendChild(li);
    });
  }
  async function openConversation(id) {
    state.conversationId = id;
    const r = await api("/api/hermes/v1/conversations/" + id);
    $("#messages").innerHTML = "";
    (r.messages || []).forEach((m) => renderMessage(m.role, m.content));
  }
  async function loadTasks() {
    if (!state.token) return;
    const r = await api("/api/hermes/v1/tasks");
    const list = $("#taskList"); list.innerHTML = "";
    (r.items || []).forEach((t) => {
      const li = document.createElement("li");
      li.innerHTML = `<div>${escapeHtml(t.title)}</div><div class="st">${escapeHtml(t.status)}</div>`;
      list.appendChild(li);
    });
  }

  // events
  $("#chatForm").addEventListener("submit", (e) => {
    e.preventDefault();
    const ta = $("#composer"); const text = ta.value.trim(); if (!text) return;
    ta.value = ""; sendMessage(text);
  });
  $("#composer").addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); $("#chatForm").requestSubmit(); }
  });
  $("#newChat").addEventListener("click", () => { state.conversationId = null; $("#messages").innerHTML = '<div class="empty">新对话已开始。</div>'; });
  $("#loginForm").addEventListener("submit", (e) => { e.preventDefault(); doLogin($("#loginUser").value, $("#loginPass").value).catch((err) => { $("#loginError").textContent = err.message; $("#loginError").hidden = false; }); });
  $("#logoutBtn").addEventListener("click", async () => {
    try { await api("/api/hermes/v1/auth/logout", { method: "POST" }); } catch (e) {}
    state.token = null; sessionStorage.removeItem("hermes_token"); $("#logoutBtn").hidden = true;
    showLogin(true); banner("已退出登录", "warn");
  });
  $("#newTask").addEventListener("click", async () => {
    const title = prompt("任务标题"); if (!title) return;
    try { await api("/api/hermes/v1/tasks", { method: "POST", idempotencyKey: crypto.randomUUID(), body: { title } }); await loadTasks(); }
    catch (e) { banner(e.message, "err"); }
  });
  $("#newLocalCmd").addEventListener("click", async () => {
    if (!state.token) { showLogin(true); return; }
    try {
      const r = await api("/api/hermes/v1/execution-nodes/" + state.deviceId + "/commands", {
        method: "POST", idempotencyKey: crypto.randomUUID(),
        body: { command_type: "local_exec", payload: { action: "open_obsidian", note: "示例命令" } },
      });
      $("#cmdResult").textContent = "命令 " + r.command_id + " 已加入队列（status=" + r.status + "）。电脑上线后执行。";
      banner("本地命令已入队，云端对话不受影响。", "warn");
    } catch (e) { banner(e.message, "err"); }
  });

  // init
  if (state.token) { $("#logoutBtn").hidden = false; refreshStatus().then(loadConversations).then(loadTasks); }
  else { showLogin(true); refreshStatus(); }
})();
