// Phase 3.0 NES topdown: WS イベント → scene.bubble + movement.visitDesk のディスパッチ。
// 旧 Phase 2.5-rev のサザン専用ポーズ (throne_*) と inferSazanPose は完全削除。
// サザンも 4方向 walk + idle のみで、玉座座位はキャラスプライト自身で表現しない (玉座家具は scene 側)。

function preview(s) {
  if (!s) return "";
  return String(s).replace(/\s+/g, " ").trim();
}

export const EVENT_HANDLERS = {
  message: (ev, scene) => {
    const text = preview(ev.details?.message || ev.details?.preview || "💬");
    scene.bubble(ev.agent, text || "💬", 3500);
  },

  consult: (ev, scene, movement) => {
    const target = ev.details?.to;
    if (target && target !== ev.agent) {
      movement?.visitDesk(ev.agent, target, 1500);
    }
    scene.bubble(ev.agent, "💬 相談中…", 2500);
  },

  dispatch: (ev, scene, movement) => {
    const assignee = ev.details?.assigned_to;
    if (assignee && assignee !== ev.agent) {
      movement?.visitDesk(ev.agent, assignee, 1400);
    }
    scene.bubble(ev.agent, "📨 指示を出した", 2000);
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
      movement?.visitDesk(ev.agent, target, 800);
    }
  },

  delivery: (ev, scene) => {
    scene.bubble(ev.agent, "📦 納品！", 4000);
  },

  report: (ev, scene, movement) => {
    scene.bubble(ev.agent, "✅ 報告", 2200);
    movement?.settleAt(ev.agent, "down");
  },

  order_queued: (_ev, scene) => {
    scene.bubble("yuko", "📩 新着案件", 2500);
  },

  // typing 状態廃止 (NES では区別なし)
  agent_start:    () => {},
  status_change:  () => {},
  tool_use:       () => {},
  thinking:       () => {},
};

export function dispatch(ev, scene, movement) {
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
