// WS イベントの event_type → 描画指示 (吹き出し + 歩行アニメ) のディスパッチテーブル。
// scene には bubble(agent, text, ttl) と charactersById が生えている。
// animator には walkTo / visitDesk / settleAt が生えている。

function preview(s) {
  if (!s) return "";
  return String(s).replace(/\s+/g, " ").trim();
}

// サザンの口調から推測してポーズを返す。マッチしない場合は null (= 通常 talking)。
function inferSazanPose(text) {
  if (!text) return null;
  const s = String(text);
  if (/[ふフ]ハハ|高笑/.test(s)) return "fuhahaha_laughing";
  if (/許す|よかろう|認め[るた]/.test(s)) return "nod_approve";
  if (/ならぬ|却下|許さ[ぬん]/.test(s)) return "hand_stop";
  if (/愛|温もり|お師さん/.test(s)) return "thinking_hand_chin";
  if (/負け|及ば[ぬん]|フッ、フフ/.test(s)) return "accept_defeat";
  if (/ひかぬ|媚びぬ|省みぬ|帝王/.test(s)) return "fist_raised";
  if (/制圧前進|滅びよ/.test(s)) return "proclaim_arms_wide";
  return null;
}

export const EVENT_HANDLERS = {
  message: (ev, scene, animator) => {
    const text = preview(ev.details?.message || ev.details?.preview || "💬");
    scene.bubble(ev.agent, text || "💬", 3500);
    // サザンが話す時は内容に応じたポーズを取らせる (3 秒 → idle)
    if (ev.agent === "souther" && animator) {
      const pose = inferSazanPose(text) || "talking";
      animator.strikePose("souther", pose, 3000);
    }
  },

  consult: (ev, scene, animator) => {
    const target = ev.details?.to;
    if (target && target !== ev.agent) {
      animator?.visitDesk(ev.agent, target, 1500);
    }
    scene.bubble(ev.agent, "💬 相談中…", 2500);
    // サザンが相談を受ける側 (consult_souther) なら思索ポーズ
    if (target === "souther" && animator) {
      animator.strikePose("souther", "thinking_hand_chin", 4000);
    }
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

    // サザンが裁定する場合は専用ポーズ
    if (ev.agent === "souther" && animator) {
      const pose = v === "approve"   ? "nod_approve"
                 : v === "revise"    ? "hand_stop"
                 : v === "escalate_to_president" ? "fist_raised"
                 :                      "point_decree_right";
      animator.strikePose("souther", pose, 2500);
    }

    // 対象の机方向へ短い visit (target_agent or target_subtask の assignee)
    const target = ev.details?.target_agent;
    if (target && target !== ev.agent) {
      animator?.visitDesk(ev.agent, target, 800);
    }
  },

  delivery: (ev, scene, animator) => {
    scene.bubble(ev.agent, "📦 納品！", 4000);
    // サザンが納品報告を受けたら高笑い
    if (ev.agent === "souther" && animator) {
      animator.strikePose("souther", "fuhahaha_laughing", 3000);
    }
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
