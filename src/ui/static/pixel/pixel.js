// 愛帝十字陵 — ピクセル UI エントリポイント
// WS 接続 + サイドパネル制御 + シーン構築のオーケストレーション

import { createScene } from "/pixel-static/scene.js";
import { dispatch } from "/pixel-static/eventMap.js";
import { CHAR_DEFS } from "/pixel-static/characters.js";
import { loadCharSheet, loadDesks, loadBackground, loadDecor } from "/pixel-static/spriteLoader.js";
import { makeMovement } from "/pixel-static/movement.js";

// ---- DOM 参照 ----
const $ = (sel) => document.querySelector(sel);
const wsDot   = $("#ws-dot");
const wsLabel = $("#ws-label");
const panel   = $("#profile-panel");
const panelIcon = $("#panel-icon");
const panelName = $("#panel-name");
const panelRole = $("#panel-role");
const panelClose = $("#panel-close");
const activeCount = $("#active-count");
const activeTasks = $("#active-tasks");
const latestEvent = $("#latest-event");
const recentMessages = $("#recent-messages");

// ---- スプライト読み込み + シーン構築 ----
const [charTextures, deskTextures, backgroundTexture, decorTextures] = await Promise.all([
  loadCharSheet(),    // 5 キャラ × 4方向 × 2フレーム = 40 frame (Phase 3.0)
  loadDesks(),        // 5 デスク (souther 1x3 / yuko 2x3 凹型 / 三兄弟 1x2) (v4.1)
  loadBackground(),   // オフィス 1 枚絵背景 1024x768 (v4.2、目チカチカ防止)
  loadDecor(),        // 壁装飾 (社訓額縁など) (v4.3)
]);
const scene = await createScene($("#pixi-root"), {
  onCharClick: openPanel,
  charTextures,
  deskTextures,
  backgroundTexture,
  decorTextures,
});
const movement = makeMovement(scene.charactersById);

// 会話パネルの TTL が満了したら、相手から「返答」を受けたケースに限って
// dwell 中の visitor を帰宅させる。
// 判定: lastSpeaker !== id の場合のみ release。これにより、
//  - 自発パネルだけが消えた (返答未着) → visitor は安全弁 (movement の SAFETY_DWELL_MS=120s) まで待機
//  - 相手の返答パネルが消えた → visitor は即座に帰路
scene.dialog.setOnTtlExpire(({ left, right, lastSpeaker }) => {
  for (const id of [left, right]) {
    if (!id || !movement.isDwelling(id)) continue;
    if (lastSpeaker && lastSpeaker !== id) {
      movement.releaseVisitor(id);
    }
  }
});

window.__pixelDebug = {
  scene,
  movement,
  dispatch: (ev) => dispatch(ev, scene, movement),
};

// ---- WebSocket ----
// 接続直後はサーバが過去 100 件のスナップショットを一気に送ってくる。
// これらは "今このタイミング" のイベントではないので、
// 描画 (吹き出し / 歩行) を抑止して state だけを最新に追従させる。
const SNAPSHOT_QUIET_MS = 1500;
let snapshotEnd = 0;

function connectWs() {
  const proto = location.protocol === "https:" ? "wss:" : "ws:";
  const url = `${proto}//${location.host}/ws/events`;
  const ws = new WebSocket(url);

  ws.addEventListener("open", () => {
    wsDot.classList.remove("offline");
    wsDot.classList.add("online");
    wsLabel.textContent = "connected";
    snapshotEnd = Date.now() + SNAPSHOT_QUIET_MS;
  });

  ws.addEventListener("close", () => {
    wsDot.classList.remove("online");
    wsDot.classList.add("offline");
    wsLabel.textContent = "disconnected — 再接続中…";
    setTimeout(connectWs, 2000);
  });

  ws.addEventListener("error", () => { /* close で拾う */ });

  ws.addEventListener("message", (e) => {
    let data;
    try { data = JSON.parse(e.data); } catch { return; }
    if (data?.type !== "event") return;

    // スナップショット期間中は描画を抑止 (state 切替も歩行も止める)
    if (Date.now() < snapshotEnd) return;

    dispatch(data, scene, movement);
  });
}
connectWs();

// ---- サイドパネル ----
let currentAbort = null;

async function openPanel(agent) {
  const def = CHAR_DEFS[agent];
  if (!def) return;

  panelIcon.textContent = def.icon;
  panelName.textContent = def.name;
  panelRole.textContent = def.role;
  activeCount.textContent = "…";
  activeTasks.innerHTML = '<li class="empty">読み込み中…</li>';
  latestEvent.textContent = "—";
  recentMessages.innerHTML = '<li class="empty">読み込み中…</li>';
  panel.hidden = false;

  if (currentAbort) currentAbort.abort();
  const ctl = new AbortController();
  currentAbort = ctl;

  try {
    const res = await fetch(`/api/staff/${encodeURIComponent(agent)}/profile`, { signal: ctl.signal });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    renderPanel(data);
  } catch (err) {
    if (err.name === "AbortError") return;
    activeTasks.innerHTML = `<li class="empty">読み込み失敗: ${escapeHtml(err.message)}</li>`;
    recentMessages.innerHTML = "";
    latestEvent.textContent = "—";
  }
}

function renderPanel(data) {
  // active_tasks
  const tasks = data.active_tasks || [];
  activeCount.textContent = tasks.length;
  if (tasks.length === 0) {
    activeTasks.innerHTML = '<li class="empty">担当中の案件はありません</li>';
  } else {
    activeTasks.innerHTML = tasks
      .map((t) => `
        <li>
          <div>${escapeHtml(t.title || "(無題)")}<span class="status" data-status="${escapeHtml(t.status || "")}">${escapeHtml(t.status || "")}</span></div>
        </li>
      `)
      .join("");
  }

  // latest_event
  const ev = data.latest_event;
  if (ev) {
    const msg = ev.details?.message || ev.details?.preview || "";
    latestEvent.textContent = `${ev.event_type}${msg ? ": " + msg : ""}`;
  } else {
    latestEvent.textContent = "(直近の自発イベントなし)";
  }

  // recent_messages
  const msgs = data.recent_messages || [];
  if (msgs.length === 0) {
    recentMessages.innerHTML = '<li class="empty">過去のやり取りはありません</li>';
  } else {
    recentMessages.innerHTML = msgs
      .map((m) => {
        const ts = formatTs(m.timestamp);
        const from = displayName(m.from_agent);
        const to = displayName(m.to_agent);
        const body = (m.content || "").slice(0, 200);
        return `
          <li>
            <div class="meta">[${escapeHtml(ts)}] ${escapeHtml(from)}<span class="arrow">→</span>${escapeHtml(to)}</div>
            <div class="body">${escapeHtml(body)}</div>
          </li>
        `;
      })
      .join("");
  }
}

function displayName(agent) {
  return CHAR_DEFS[agent]?.name || agent || "?";
}

function formatTs(iso) {
  if (!iso) return "";
  try {
    const d = new Date(iso);
    const pad = (n) => String(n).padStart(2, "0");
    return `${pad(d.getMonth() + 1)}/${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
  } catch {
    return iso;
  }
}

function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[c]);
}

// パネルを閉じる
panelClose.addEventListener("click", () => {
  panel.hidden = true;
});
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") panel.hidden = true;
});
