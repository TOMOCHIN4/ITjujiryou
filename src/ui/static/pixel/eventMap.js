// WS イベントの event_type → 描画指示 (吹き出し + 歩行アニメ) のディスパッチテーブル。
// scene には bubble(agent, text, ttl) と charactersById が生えている。
// animator には walkTo / visitDesk / settleAt が生えている。

function preview(s) {
  if (!s) return "";
  return String(s).replace(/\s+/g, " ").trim();
}

export const EVENT_HANDLERS = {
  message: (ev, scene) => {
    const text = preview(ev.details?.message || ev.details?.preview || "💬");
    scene.bubble(ev.agent, text || "💬", 3500);
  },

  consult: (ev, scene, animator) => {
    const target = ev.details?.to;
    if (target && target !== ev.agent) {
      animator?.visitDesk(ev.agent, target, 1500);
    }
    scene.bubble(ev.agent, "💬 相談中…", 2500);
  },

  dispatch: (ev, scene, animator) => {
    // dispatch_task は通常 yuko 発・assigned_to が宛先
    const assignee = ev.details?.assigned_to;
    if (assignee && assignee !== ev.agent) {
      animator?.visitDesk(ev.agent, assignee, 1400);
    }
    scene.bubble(ev.agent, "📨 指示を出した", 2000);
  },

  plan: (ev, scene) => {
    scene.bubble(ev.agent, "📋 プラン作成", 2000);
  },

  evaluate: (ev, scene, animator) => {
    const v = ev.details?.decision;
    const tag = v === "approve"
      ? "✅ 承認"
      : v === "revise"
      ? "↩ 差戻"
      : v === "escalate_to_president"
      ? "👑 上申"
      : "🔍 評価";
    scene.bubble(ev.agent, tag, 2500);

    // 対象の机方向へ短い visit (target_agent or target_subtask の assignee)
    const target = ev.details?.target_agent;
    if (target && target !== ev.agent) {
      animator?.visitDesk(ev.agent, target, 800);
    }
  },

  delivery: (ev, scene) => {
    scene.bubble(ev.agent, "📦 納品！", 4000);
  },

  // 部下完了報告 — Phase 1 では未知扱いだったが Phase 2 で正式採用
  report: (ev, scene, animator) => {
    scene.bubble(ev.agent, "✅ 報告", 2200);
    // typing 状態から idle に戻す
    animator?.settleAt(ev.agent, "idle");
  },

  order_queued: (_ev, scene) => {
    // クライアント発注は yuko の頭上に表示
    scene.bubble("yuko", "📩 新着案件", 2500);
  },

  // 部下が新着メッセージで起動した瞬間 — typing 状態に切替
  agent_start: (ev, _scene, animator) => {
    animator?.settleAt(ev.agent, "typing");
  },

  status_change: () => {
    // Phase 2 では描画ノイズ防止で無視
  },

  // ツール呼び出し中 — 連続発火するので吹き出しは出さず state だけ更新
  tool_use: (ev, _scene, animator) => {
    animator?.settleAt(ev.agent, "typing");
  },

  thinking: () => {
    // 思考中は無視 (大量発火するため)
  },
};

export function dispatch(ev, scene, animator) {
  const handler = EVENT_HANDLERS[ev.event_type];
  if (handler) {
    try {
      handler(ev, scene, animator);
    } catch (err) {
      console.error("[pixel] handler error for", ev.event_type, err);
    }
  } else {
    if (typeof console !== "undefined") {
      console.debug("[pixel] unknown event_type:", ev.event_type, ev);
    }
  }
}
