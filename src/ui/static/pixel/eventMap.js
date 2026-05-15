// Phase 3.0 NES topdown: WS イベント → scene.bubble + scene.emailPopup + scene.dialog + movement.visitDesk のディスパッチ。
// movementRules.canPhysicallyMove で物理移動を gate し、isClientInteraction でメール popup へ早期 route。
// bubble は動作キュー (transient)、dialog パネルは会話ログ (lingering 8 秒)、両者を共存させる。

import { canPhysicallyMove, isClientInteraction } from "/pixel-static/movementRules.js";

// 訪問先で滞在する時間 (ms)。会話パネル TTL と揃えて、相手の応答パネルが
// 消えるまで visitor が host 席に待機する見せ方にする。
const DWELL_MS = 8000;
// 三兄弟が L 字経路でユウコ席まで歩く所要時間 (約 720ms) より少し余裕を持たせた値。
// report 時はこの時間だけ bubble / panel の発火を遅延させて「ユウコの所に着いてから発信」する。
const REPORT_ARRIVAL_DELAY_MS = 800;

const BROTHERS = new Set(["writer", "designer", "engineer"]);

function preview(s) {
  if (!s) return "";
  // backend 側 mcp_server._extract_preview と意味的に同じ二重防御。
  // 「【...】」「(subtask: ...)」を除去 → 「---」/「# 見出し」で切る → 連続空白を圧縮。
  return String(s)
    .replace(/^【[^】]*】\s*/, "")
    .replace(/\s*\(subtask(?:_id)?:\s*[^)]+\)/g, "")
    .split(/\n---\s*\n|\n---\s*$|^---\s*\n/)[0]
    .split(/\n#+\s/)[0]
    .replace(/\s+/g, " ")
    .trim();
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

/** 部下/社長/秘書のいずれか (= 事務所内キャラ) か。 */
function isStaffAgent(id) {
  return id && id !== "client" && id !== "system";
}

// 裏側 silent モード (persona_narrative.md §6.6) のメッセージタイプ。
// pixel UI には一切描画しない (痕跡を残さない)。
const BACKSTAGE_MESSAGE_TYPES = new Set(["curator_request", "curator_response"]);

export const EVENT_HANDLERS = {
  message: (ev, scene, movement) => {
    const text = preview(ev.details?.message || ev.details?.preview || "💬");
    const to = ev.details?.to_agent;
    const messageType = ev.details?.message_type || "";

    // 裏側 silent モードは UI 描画 skip (二重構造の裏は表側 omage 発火まで隠す)
    if (BACKSTAGE_MESSAGE_TYPES.has(messageType)) {
      return;
    }

    // 三兄弟 → ユウコ への完了報告は、必ずユウコ席まで歩いてから発信する。
    // 自席発の bubble + 受信 bubble + パネルは到着後に遅延発火させる。
    const isReportFromBrother = messageType === "report"
      && BROTHERS.has(ev.agent)
      && to === "yuko";

    const fireBubblesAndPanel = () => {
      scene.bubble(ev.agent, text || "💬", 3500);
      if (to && to !== ev.agent && to !== "client") {
        bubbleListener(scene, to, "message");
        if (isStaffAgent(ev.agent) && isStaffAgent(to)) {
          scene.dialog?.showPair({
            speaker: ev.agent,
            listener: to,
            action: messageType === "report" ? "✅ 報告" : "💬 発信",
            listenerAction: "👂 受信",
            body: text,
          });
        }
      }
    };

    if (isReportFromBrother && canPhysicallyMove(ev.agent, to)) {
      movement?.visitDesk(ev.agent, to, DWELL_MS);
      setTimeout(fireBubblesAndPanel, REPORT_ARRIVAL_DELAY_MS);
    } else {
      fireBubblesAndPanel();
    }
  },

  consult: (ev, scene, movement) => {
    const target = ev.details?.to;
    const text = preview(ev.details?.preview || ev.details?.message || "");
    scene.bubble(ev.agent, "💬 相談中…", 2500);
    if (target && target !== ev.agent) {
      if (canPhysicallyMove(ev.agent, target)) {
        movement?.visitDesk(ev.agent, target, DWELL_MS);
      }
      bubbleListener(scene, target, "consult");
      if (isStaffAgent(ev.agent) && isStaffAgent(target)) {
        scene.dialog?.showPair({
          speaker: ev.agent,
          listener: target,
          action: "💬 相談中",
          listenerAction: "👂 相談を受けた",
          body: text,
        });
      }
    }
  },

  dispatch: (ev, scene, movement) => {
    const assignee = ev.details?.assigned_to;
    const subject = ev.details?.subject || "";
    const text = preview(ev.details?.preview || "");
    scene.bubble(ev.agent, "📨 指示を出した", 2000);
    if (assignee && assignee !== ev.agent) {
      if (canPhysicallyMove(ev.agent, assignee)) {
        movement?.visitDesk(ev.agent, assignee, DWELL_MS);
      }
      bubbleListener(scene, assignee, "dispatch");
      if (isStaffAgent(ev.agent) && isStaffAgent(assignee)) {
        scene.dialog?.showPair({
          speaker: ev.agent,
          listener: assignee,
          action: "📨 指示",
          listenerAction: "📥 受領",
          subject,
          body: text,
        });
      }
    }
  },

  plan: (ev, scene) => {
    scene.bubble(ev.agent, "📋 プラン作成", 2000);
  },

  evaluate: (ev, scene, _movement) => {
    const v = ev.details?.decision;
    const tag = v === "approve" ? "✅ 承認"
              : v === "revise"  ? "↩ 差戻"
              : v === "escalate_to_president" ? "👑 上申"
              :                    "🔍 評価";
    scene.bubble(ev.agent, tag, 2500);
    const target = ev.details?.target_agent;
    if (target && target !== ev.agent) {
      // ユウコ→部下 の物理移動はしない (席は動かさず、bubble + 壁面パネルだけ出す)
      bubbleListener(scene, target, "evaluate");
      if (isStaffAgent(ev.agent) && isStaffAgent(target)) {
        scene.dialog?.showPair({
          speaker: ev.agent,
          listener: target,
          action: tag,
          listenerAction: "🙇 評価を受けた",
          body: preview(ev.details?.preview || ""),
        });
      }
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

  thought: (ev, scene) => {
    // ユウコ (将来は他キャラも) の独白。bubble は出さない (画面ノイズ抑制) — パネルだけ更新。
    const agent = ev.details?.agent || ev.agent;
    const text = preview(ev.details?.preview || ev.details?.message || "");
    if (!agent || !text) return;
    scene.dialog?.addThought({ agent, text });
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
    // ユウコパネル (右) にもメールサマリを並走表示
    scene.dialog?.showSingle({
      agent: "yuko",
      action: isIncoming ? "📩 受信メール" : "📤 送信メール",
      subject: ev.details?.subject || "",
      body: ev.details?.preview || ev.details?.message || "",
    });
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
