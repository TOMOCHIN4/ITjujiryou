// Phase 3.0 NES topdown: WS イベント → scene.bubble + scene.emailPopup + movement.visitDesk のディスパッチ。
// movementRules.canPhysicallyMove で物理移動を gate し、isClientInteraction でメール popup へ早期 route。

import { canPhysicallyMove, isClientInteraction } from "/pixel-static/movementRules.js";

function preview(s) {
  if (!s) return "";
  return String(s).replace(/\s+/g, " ").trim();
}

/** speaker の bubble + listener (host) の受信 bubble を出すヘルパ。 */
function bubbleListener(scene, listener, kind) {
  if (!listener) return;
  const tag = kind === "consult"  ? "👂 相談を受けた"
            : kind === "dispatch" ? "📥 指示を受けた"
            : kind === "evaluate" ? "🙇 評価を受けた"
            : kind === "message"  ? "👂 受信"
            :                       "👂";
  scene.bubble(listener, tag, 2200);
}

export const EVENT_HANDLERS = {
  message: (ev, scene) => {
    const text = preview(ev.details?.message || ev.details?.preview || "💬");
    scene.bubble(ev.agent, text || "💬", 3500);
    const to = ev.details?.to_agent;
    if (to && to !== ev.agent && to !== "client") {
      bubbleListener(scene, to, "message");
    }
  },

  consult: (ev, scene, movement) => {
    const target = ev.details?.to;
    scene.bubble(ev.agent, "💬 相談中…", 2500);
    if (target && target !== ev.agent) {
      if (canPhysicallyMove(ev.agent, target)) {
        movement?.visitDesk(ev.agent, target, 1500);
      }
      bubbleListener(scene, target, "consult");
    }
  },

  dispatch: (ev, scene, movement) => {
    const assignee = ev.details?.assigned_to;
    scene.bubble(ev.agent, "📨 指示を出した", 2000);
    if (assignee && assignee !== ev.agent) {
      if (canPhysicallyMove(ev.agent, assignee)) {
        movement?.visitDesk(ev.agent, assignee, 1400);
      }
      bubbleListener(scene, assignee, "dispatch");
    }
  },

  plan: (ev, scene) => {
    scene.bubble(ev.agent, "📋 プラン作成", 2000);
  },

  evaluate: (ev, scene, movement) => {
    const v = ev.details?.decision;
    const tag = v === "approve" ? "✅ 承認"
              : v === "revise"  ? "↩ 差戻"
              : v === "escalate_to_president" ? "👑 上申"
              :                    "🔍 評価";
    scene.bubble(ev.agent, tag, 2500);
    const target = ev.details?.target_agent;
    if (target && target !== ev.agent) {
      if (canPhysicallyMove(ev.agent, target)) {
        movement?.visitDesk(ev.agent, target, 800);
      }
      bubbleListener(scene, target, "evaluate");
    }
  },

  delivery: (ev, scene) => {
    // クライアントへの delivery は dispatch() 冒頭の email-route で先に処理されるため
    // ここに落ちるのは念のためのフォールバック。
    if (!isClientInteraction(ev)) {
      scene.bubble(ev.agent, "📦 納品！", 4000);
    }
  },

  report: (ev, scene, movement) => {
    scene.bubble(ev.agent, "✅ 報告", 2200);
    movement?.settleAt(ev.agent, "down");
  },

  order_queued: (_ev, scene) => {
    // クライアント発注も email-route で先に処理されるが、
    // details が無い古いログ向けに fallback bubble を維持。
    scene.bubble("yuko", "📩 新着案件", 2500);
  },

  // typing 状態廃止 (NES では区別なし)
  agent_start:    () => {},
  status_change:  () => {},
  tool_use:       () => {},
  thinking:       () => {},
};

export function dispatch(ev, scene, movement) {
  // クライアント ↔ ユウコ のメールやり取りは最優先で email popup へ
  if (isClientInteraction(ev)) {
    const isIncoming = ev.details?.from_agent === "client";
    scene.emailPopup({
      direction: isIncoming ? "incoming" : "outgoing",
      sender: isIncoming ? "client" : "yuko",
      recipient: isIncoming ? "yuko" : "client",
      subject: ev.details?.subject || (ev.event_type === "delivery" ? "📦 納品" : "📩 案件"),
      body: ev.details?.preview || ev.details?.message || "",
      ttlMs: 6000,
    });
    scene.bubble("yuko", isIncoming ? "📩" : "📤", 2000);
    return;
  }

  const handler = EVENT_HANDLERS[ev.event_type];
  if (handler) {
    try {
      handler(ev, scene, movement);
    } catch (err) {
      console.error("[pixel] handler error for", ev.event_type, err);
    }
  } else {
    if (typeof console !== "undefined") {
      console.debug("[pixel] unknown event_type:", ev.event_type, ev);
    }
  }
}
