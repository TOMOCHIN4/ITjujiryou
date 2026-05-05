// IT十字陵 ダッシュボード フロント

const STAFF_META = {
  souther:  { icon: "👑", name: "サウザー", role: "社長" },
  yuko:     { icon: "💼", name: "ユウコ",   role: "営業主任" },
  designer: { icon: "🎨", name: "デザイナー", role: "" },
  engineer: { icon: "🛠", name: "エンジニア", role: "" },
  writer:   { icon: "✍️", name: "ライター",   role: "" },
  client:   { icon: "📩", name: "クライアント", role: "" },
  system:   { icon: "⚙️", name: "system",     role: "" },
};

const KANBAN_COLUMNS = [
  ["received",    "受付"],
  ["hearing",     "ヒアリング"],
  ["approved",    "承認済"],
  ["in_progress", "作業中"],
  ["review",      "レビュー"],
  ["delivered",   "納品済"],
];

const $ = (sel) => document.querySelector(sel);

function fmtTime(iso) {
  if (!iso) return "";
  try {
    const d = new Date(iso);
    const pad = (n) => String(n).padStart(2, "0");
    return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
  } catch { return iso; }
}

function trimText(s, n = 220) {
  if (!s) return "";
  return s.length > n ? s.slice(0, n) + "…" : s;
}

// ---------- Timeline ----------
const timelineEl = () => $("#timeline");

function appendEvent(ev) {
  const el = document.createElement("div");
  const agent = ev.agent || "system";
  el.className = `tl-line ag-${agent}`;
  const ts = document.createElement("span"); ts.className = "ts"; ts.textContent = `[${fmtTime(ev.timestamp)}]`;
  const ag = document.createElement("span"); ag.className = "ag"; ag.textContent = `${(STAFF_META[agent]?.icon || "•")} ${agent}`;
  const msg = document.createElement("span");
  const details = ev.details || {};
  const m = details.message || details.raw || ev.event_type || "";
  msg.textContent = trimText(typeof m === "string" ? m : JSON.stringify(m));
  el.appendChild(ts); el.appendChild(ag); el.appendChild(msg);
  const tl = timelineEl();
  tl.appendChild(el);
  tl.scrollTop = tl.scrollHeight;
}

// ---------- Staff cards ----------
function renderStaff(staff) {
  const bar = $("#staff-bar");
  bar.innerHTML = "";
  for (const s of staff) {
    const meta = STAFF_META[s.agent] || { icon: "•", name: s.agent, role: "" };
    const card = document.createElement("div");
    card.className = "staff-card";
    card.innerHTML = `
      <div class="icon">${meta.icon}</div>
      <div>
        <div class="name">${meta.name}</div>
        <div class="role">${meta.role}</div>
      </div>
      <div class="state ${s.state}">${s.state}</div>
    `;
    bar.appendChild(card);
  }
}

const recentByAgent = new Map();
function bumpStaff(ev) {
  const a = ev.agent;
  if (!STAFF_META[a] || a === "client") return;
  recentByAgent.set(a, Date.now());
  refreshStaffStates();
}
function refreshStaffStates() {
  const cards = document.querySelectorAll(".staff-card");
  cards.forEach((c, i) => {
    const agent = ["souther","yuko","designer","engineer","writer"][i];
    const last = recentByAgent.get(agent);
    const working = last && (Date.now() - last) < 30000;
    const stateEl = c.querySelector(".state");
    if (stateEl) {
      stateEl.className = "state " + (working ? "working" : "idle");
      stateEl.textContent = working ? "working" : "idle";
    }
  });
}
setInterval(refreshStaffStates, 5000);

// ---------- Kanban ----------
function renderKanban(tasks) {
  const root = $("#kanban");
  root.innerHTML = "";
  const groups = Object.fromEntries(KANBAN_COLUMNS.map(([k]) => [k, []]));
  for (const t of tasks) {
    if (groups[t.status]) groups[t.status].push(t);
    else (groups["received"] = groups["received"] || []).push(t);
  }
  for (const [key, label] of KANBAN_COLUMNS) {
    const col = document.createElement("div"); col.className = "col";
    const h = document.createElement("h3"); h.textContent = `${label} (${groups[key].length})`;
    col.appendChild(h);
    for (const t of groups[key].slice(0, 20)) {
      const card = document.createElement("div"); card.className = "task-card";
      card.innerHTML = `<div class="title">${escapeHtml(t.title || "(untitled)")}</div>
                        <div class="meta">${t.id.slice(0,8)} · ${fmtTime(t.created_at)}</div>`;
      card.addEventListener("click", () => openTask(t.id));
      col.appendChild(card);
    }
    root.appendChild(col);
  }
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]));
}

async function openTask(id) {
  const r = await fetch(`/api/tasks/${id}`);
  if (!r.ok) return;
  const d = await r.json();
  const detail = $("#task-detail");
  const t = d.task;
  const subs = (d.subtasks || []).map(s => `<li>${escapeHtml(s.assigned_to)} · ${escapeHtml(s.status)} — ${escapeHtml(s.description || "")}</li>`).join("");
  const dels = (d.deliverables || []).map(x => {
    const path = x.file_path.replace(/^outputs[\\/]/, "");
    return `<li><a href="/outputs/${encodeURI(path)}" target="_blank">${escapeHtml(x.file_path)}</a> — ${escapeHtml(x.created_by || "")}</li>`;
  }).join("");
  detail.innerHTML = `
    <h3>${escapeHtml(t.title)}</h3>
    <p class="hint">id: ${t.id} · status: ${escapeHtml(t.status)} · 作成: ${fmtTime(t.created_at)}</p>
    <p>${escapeHtml(trimText(t.description, 500))}</p>
    <h4>サブタスク</h4><ul>${subs || "<li>なし</li>"}</ul>
    <h4>納品物</h4><ul>${dels || "<li>なし</li>"}</ul>
  `;
  $("#task-dialog").showModal();
}

// ---------- WebSocket ----------
function connectWS() {
  const url = `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws/events`;
  const ws = new WebSocket(url);
  ws.addEventListener("open", () => {
    $("#ws-dot").className = "dot online";
    $("#ws-label").textContent = "接続中";
  });
  ws.addEventListener("close", () => {
    $("#ws-dot").className = "dot offline";
    $("#ws-label").textContent = "切断（5秒後に再接続）";
    setTimeout(connectWS, 5000);
  });
  ws.addEventListener("message", (e) => {
    try {
      const ev = JSON.parse(e.data);
      appendEvent(ev);
      bumpStaff(ev);
      if (ev.event_type === "status_change") refreshTasks();
    } catch {}
  });
}

// ---------- Initial fetch ----------
async function refreshTasks() {
  const r = await fetch("/api/tasks");
  if (r.ok) renderKanban(await r.json());
}
async function refreshStaff() {
  const r = await fetch("/api/staff");
  if (r.ok) renderStaff(await r.json());
}

async function init() {
  renderStaff(["souther","yuko","designer","engineer","writer"].map(a => ({agent: a, state: "idle"})));
  await refreshTasks();
  await refreshStaff();
  connectWS();
}

// ---------- Order form ----------
$("#order-submit").addEventListener("click", async () => {
  const text = $("#order-text").value.trim();
  if (!text) return;
  const btn = $("#order-submit"); btn.disabled = true;
  $("#order-status").textContent = "発注中...（タイムラインに進行が流れます）";
  try {
    const r = await fetch("/api/orders", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({ text }),
    });
    if (!r.ok) throw new Error(await r.text());
    const d = await r.json();
    $("#order-status").textContent = `納品完了: ${d.task_id || ""}`;
    $("#order-text").value = "";
    refreshTasks();
  } catch (e) {
    $("#order-status").textContent = `エラー: ${e.message || e}`;
  } finally {
    btn.disabled = false;
  }
});

init();
