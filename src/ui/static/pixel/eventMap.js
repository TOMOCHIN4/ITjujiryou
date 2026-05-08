// WS イベントの event_type → 描画指示 (吹き出し) のディスパッチテーブル。
// scene には bubble(agent, text, ttl) が生えている。

function preview(s) {
  if (!s) return "";
  return String(s).replace(/\s+/g, " ").trim();
}

export const EVENT_HANDLERS = {
  message: (ev, scene) => {
    const text = preview(ev.details?.message || ev.details?.preview || "💬");
    scene.bubble(ev.agent, text || "💬", 3500);
  },
  consult: (ev, scene) => {
    scene.bubble(ev.agent, "💬 相談中…", 2500);
  },
  dispatch: (ev, scene) => {
    scene.bubble(ev.agent, "📨 指示を出した", 2000);
  },
  plan: (ev, scene) => {
    scene.bubble(ev.agent, "📋 プラン作成", 2000);
  },
  evaluate: (ev, scene) => {
    const v = ev.details?.decision;
    const tag = v === "approve"
      ? "✅ 承認"
      : v === "revise"
      ? "↩ 差戻"
      : v === "escalate_to_president"
      ? "👑 上申"
      : "🔍 評価";
    scene.bubble(ev.agent, tag, 2500);
  },
  delivery: (ev, scene) => {
    scene.bubble(ev.agent, "📦 納品！", 4000);
  },
  order_queued: (_ev, scene) => {
    // クライアント発注は yuko の頭上に表示する (発注元 client にはキャラがいないため)
    scene.bubble("yuko", "📩 新着案件", 2500);
  },
  status_change: () => {
    // Phase 1 では描画ノイズ防止で無視
  },
};

export function dispatch(ev, scene) {
  const handler = EVENT_HANDLERS[ev.event_type];
  if (handler) {
    handler(ev, scene);
  } else {
    // 未知の event_type は debug ログのみ (落とさない)
    if (typeof console !== "undefined") {
      console.debug("[pixel] unknown event_type:", ev.event_type, ev);
    }
  }
}
