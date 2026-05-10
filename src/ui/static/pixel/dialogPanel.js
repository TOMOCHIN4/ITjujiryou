// 壁面 2 枠の会話パネル overlay。social UI の "会話ログ" 役。
// HTML overlay を #pixi-root に absolute で重ねる (emailPopup と同じ流儀)。
// TTL 8 秒固定。新ペアが来たら旧ペアを即 fade out。
// 心のうち (thought) は当該キャラのパネルへ inner 領域で追記、TTL リセット。

import {
  resolveSlots,
  soloSide,
  CHAR_CSS_COLOR,
  charName,
  charRole,
} from "/pixel-static/dialogLayout.js";

const TTL_MS = 8000;
const FADE_MS = 220;

/**
 * @param {HTMLElement} parentEl 親要素 (#pixi-root を想定、position: relative 必須)
 */
export function mountDialogPanelLayer(parentEl) {
  const layer = document.createElement("div");
  layer.className = "dialog-panel-layer";
  parentEl.appendChild(layer);

  /** 現在表示中のスロット情報。
   *  state.slots = { left: { agent, el } | null, right: { agent, el } | null }
   *  state.pairKey = "a-b" (ソート済) or "solo:agent"
   *  state.ttlTimer = setTimeout id
   */
  const state = {
    slots: { left: null, right: null },
    pairKey: null,
    ttlTimer: null,
    // 最後に showPair で渡された speaker。「自発パネル」と「返答パネル」を区別するため、
    // onTtlExpire callback でこの値を外に渡す。dialog 側ではロジック判断はしない。
    lastSpeaker: null,
  };

  // TTL 満了時 (= パネルが自然消失するタイミング) のコールバック。
  // 訪問者が「相手の返答パネルが消えるまで席に残る」を実現するために、
  // movement.releaseVisitor を呼ぶ wire 用。
  let onTtlExpireCallback = null;

  function pairKeyOf(a, b) {
    if (!b) return `solo:${a}`;
    return [a, b].sort().join("-");
  }

  function clearTimer() {
    if (state.ttlTimer) {
      clearTimeout(state.ttlTimer);
      state.ttlTimer = null;
    }
  }

  function scheduleClear() {
    clearTimer();
    state.ttlTimer = setTimeout(() => {
      // クリア前に slot agent + lastSpeaker を抜き出してコールバック発火
      const left = state.slots.left?.agent ?? null;
      const right = state.slots.right?.agent ?? null;
      const lastSpeaker = state.lastSpeaker;
      if (onTtlExpireCallback) {
        try {
          onTtlExpireCallback({ left, right, lastSpeaker });
        } catch (err) {
          console.error("[dialogPanel] onTtlExpire error:", err);
        }
      }
      clear();
    }, TTL_MS);
  }

  function setOnTtlExpire(cb) {
    onTtlExpireCallback = cb;
  }

  function removeSlot(side) {
    const slot = state.slots[side];
    if (!slot) return;
    const el = slot.el;
    el.classList.add("dismiss");
    setTimeout(() => el.remove(), FADE_MS);
    state.slots[side] = null;
  }

  function clearAll() {
    removeSlot("left");
    removeSlot("right");
    state.pairKey = null;
    state.lastSpeaker = null;
    clearTimer();
  }

  function clear() {
    clearAll();
  }

  function buildPanel({ agent, side, action, subject, body, innerText }) {
    const el = document.createElement("div");
    el.className = `dialog-panel dialog-panel--${side}`;
    el.dataset.char = agent;
    const color = CHAR_CSS_COLOR[agent] || "#b18cff";
    el.style.setProperty("--accent-color", color);

    const header = document.createElement("header");
    header.className = "dialog-panel__header";
    const nameEl = document.createElement("span");
    nameEl.className = "dialog-panel__name";
    nameEl.textContent = charName(agent);
    const roleEl = document.createElement("span");
    roleEl.className = "dialog-panel__role";
    roleEl.textContent = charRole(agent);
    header.append(nameEl, roleEl);
    el.appendChild(header);

    if (action) {
      const actionEl = document.createElement("div");
      actionEl.className = "dialog-panel__action";
      actionEl.textContent = action;
      el.appendChild(actionEl);
    }

    if (subject) {
      const subjEl = document.createElement("div");
      subjEl.className = "dialog-panel__subject";
      subjEl.textContent = subject;
      el.appendChild(subjEl);
    }

    if (body) {
      const bodyEl = document.createElement("p");
      bodyEl.className = "dialog-panel__text";
      bodyEl.textContent = body;
      el.appendChild(bodyEl);
    }

    if (innerText) {
      el.appendChild(buildInner(innerText));
    }

    return el;
  }

  function buildInner(text) {
    const inner = document.createElement("div");
    inner.className = "dialog-panel__inner";
    const label = document.createElement("span");
    label.className = "dialog-panel__inner-label";
    label.textContent = "💭 心のうち";
    inner.appendChild(label);
    const textNode = document.createElement("span");
    textNode.textContent = text;
    inner.appendChild(textNode);
    return inner;
  }

  function placeSlot(side, opts) {
    // 既存の同 side パネルがあれば差し替え (連続イベントで上書き)
    if (state.slots[side]) {
      removeSlot(side);
    }
    const el = buildPanel({ ...opts, side });
    layer.appendChild(el);
    state.slots[side] = { agent: opts.agent, el };
    requestAnimationFrame(() => el.classList.add("show"));
  }

  /**
   * ペア会話を表示。speaker 側に action + body、listener 側に listenerAction を出す。
   * @param {object} opts
   * @param {string} opts.speaker    発信者の agent ID (= action / body の主)
   * @param {string} opts.listener   受信者の agent ID
   * @param {string} [opts.action]      speaker パネルのアクションタグ (例 "💬 相談中")
   * @param {string} [opts.listenerAction] listener パネルのアクションタグ (例 "👂 受信")
   * @param {string} [opts.subject]  speaker パネルに subject (任意)
   * @param {string} [opts.body]     speaker パネル本文 (preview)
   */
  function showPair(opts) {
    const { speaker, listener } = opts;
    const slots = resolveSlots(speaker, listener);
    if (!slots) return;

    const newKey = pairKeyOf(speaker, listener);
    if (state.pairKey && state.pairKey !== newKey) {
      // 別ペアが来た → 旧クリア
      clearAll();
    }
    state.pairKey = newKey;
    state.lastSpeaker = speaker;

    // どちらが speaker / listener か判定して slot に振る
    const speakerSide = slots.left === speaker ? "left" : "right";
    const listenerSide = speakerSide === "left" ? "right" : "left";

    placeSlot(speakerSide, {
      agent: speaker,
      action: opts.action || "",
      subject: opts.subject || "",
      body: opts.body || "",
    });
    placeSlot(listenerSide, {
      agent: listener,
      action: opts.listenerAction || "",
    });

    scheduleClear();
  }

  /**
   * 単独表示 (片側のみ)。発信者・受信者が判らない / 一人独白 用。
   * @param {object} opts
   * @param {string} opts.agent
   * @param {string} [opts.action]
   * @param {string} [opts.subject]
   * @param {string} [opts.body]
   * @param {string} [opts.innerText]  心のうち本文 (任意)
   * @param {"left"|"right"} [opts.slot]  既定はキャラの soloSide
   */
  function showSingle(opts) {
    const side = opts.slot || soloSide(opts.agent);
    const newKey = pairKeyOf(opts.agent, null);
    if (state.pairKey && state.pairKey !== newKey) {
      clearAll();
    }
    state.pairKey = newKey;

    placeSlot(side, {
      agent: opts.agent,
      action: opts.action || "",
      subject: opts.subject || "",
      body: opts.body || "",
      innerText: opts.innerText || "",
    });
    scheduleClear();
  }

  /**
   * 心のうちを当該キャラの inner 領域に追記。
   * - 既にそのキャラのパネルがアクティブなら inner を差し替え + TTL リセット
   * - 非アクティブなら showSingle で開く
   * @param {object} opts
   * @param {string} opts.agent
   * @param {string} opts.text
   */
  function addThought(opts) {
    const { agent, text } = opts;
    if (!agent || !text) return;

    // 既存パネルに当該キャラがいるか
    const existingSide = state.slots.left?.agent === agent ? "left"
                       : state.slots.right?.agent === agent ? "right"
                       : null;
    if (existingSide) {
      const slot = state.slots[existingSide];
      // 既存 inner を消して入れ替え
      const oldInner = slot.el.querySelector(".dialog-panel__inner");
      if (oldInner) oldInner.remove();
      slot.el.appendChild(buildInner(text));
      scheduleClear();
      return;
    }

    // 非アクティブ → 単独表示で心のうちだけを出す
    showSingle({
      agent,
      action: "💭 心のうち",
      innerText: text,
    });
  }

  function destroy() {
    clearAll();
    layer.remove();
  }

  return { showPair, showSingle, addThought, clear, destroy, setOnTtlExpire };
}
