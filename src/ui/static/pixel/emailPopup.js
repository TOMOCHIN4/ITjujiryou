// クライアント ↔ ユウコ のメールやり取りを HTML overlay で表示。
// canvas の上 (右上) にカードを積み重ねて、~6s で auto-dismiss。

const MAX_VISIBLE = 3;
const DEFAULT_TTL_MS = 6000;

/**
 * #pixi-root の右上にメールカード layer を作って show() ハンドルを返す。
 * @param {HTMLElement} parentEl 親要素 (#pixi-root を想定、position: relative 必須)
 * @returns {{ show: (opts) => void, destroy: () => void }}
 */
export function mountEmailPopupLayer(parentEl) {
  const layer = document.createElement("div");
  layer.className = "email-popup-layer";
  parentEl.appendChild(layer);

  /**
   * @param {{direction: "incoming"|"outgoing", sender: string, recipient: string, subject: string, body: string, ttlMs?: number}} opts
   */
  function show(opts) {
    const {
      direction = "incoming",
      sender = "?",
      recipient = "?",
      subject = "",
      body = "",
      ttlMs = DEFAULT_TTL_MS,
    } = opts || {};

    const card = document.createElement("div");
    card.className = `email-card ${direction}`;

    const senderLabel = senderToLabel(sender);
    const recipientLabel = senderToLabel(recipient);
    const icon = direction === "incoming" ? "📩" : "📤";

    card.innerHTML = `
      <div class="email-header">
        <span class="email-icon">${icon}</span>
        <span class="email-route">From: <b>${escapeHtml(senderLabel)}</b> → To: <b>${escapeHtml(recipientLabel)}</b></span>
      </div>
      ${subject ? `<div class="email-subject">${escapeHtml(subject)}</div>` : ""}
      ${body ? `<div class="email-body">${escapeHtml(body)}</div>` : ""}
      <div class="email-progress"></div>
    `;

    layer.appendChild(card);

    // 古いカードをトリム
    while (layer.children.length > MAX_VISIBLE) {
      const old = layer.firstElementChild;
      if (old) old.classList.add("dismiss");
      setTimeout(() => old?.remove(), 250);
      break; // 1 枚ずつ
    }

    // フェードイン
    requestAnimationFrame(() => card.classList.add("show"));

    // 進行バー
    const progress = card.querySelector(".email-progress");
    if (progress) {
      progress.style.transition = `transform ${ttlMs}ms linear`;
      requestAnimationFrame(() => { progress.style.transform = "scaleX(0)"; });
    }

    // auto-dismiss
    setTimeout(() => {
      card.classList.add("dismiss");
      setTimeout(() => card.remove(), 250);
    }, ttlMs);
  }

  function destroy() {
    layer.remove();
  }

  return { show, destroy };
}

function senderToLabel(agent) {
  switch (agent) {
    case "client":   return "顧客";
    case "yuko":     return "ユウコ";
    case "souther":  return "サザン";
    case "writer":   return "ハオウ";
    case "designer": return "トシ";
    case "engineer": return "センシロウ";
    default:         return agent;
  }
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
