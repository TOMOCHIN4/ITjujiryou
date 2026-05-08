// 吹き出し (SpeechBubble) — GSAP 連動。
// 入場: scale 0 → 1 with back.out, alpha 0 → 1
// 滞在: 0.4s 目に小さな yoyo jitter (rotation ±1.5°)
// 退場: scale → 0.85, alpha → 0 with power2.in

import { gsap } from "/pixel-static/animation.js";

const PADDING_X = 8;
const PADDING_Y = 5;
const FONT_SIZE = 12;
const STACK_GAP = 4;

/**
 * 吹き出しを overlayLayer に追加。
 * @param {PIXI.Container} overlayLayer
 * @param {{x:number,y:number}} charDef    キャラ座標 (現在位置)
 * @param {string} text                   表示文
 * @param {number} ttlMs                  ms で消える
 * @param {Map<string, Array>} stacks     キャラごとの活きてるバブル配列 (積み上げ管理)
 * @param {string} agent                  キャラID
 * @param {() => {x:number,y:number}} getPos  キャラ現在位置 getter (歩行中の追従用、任意)
 */
export function spawnBubble(overlayLayer, charDef, text, ttlMs, stacks, agent, getPos = null) {
  const container = new PIXI.Container();
  container.zIndex = 30;
  container.pivot.set(0, 0);

  const label = new PIXI.Text({
    text: clampText(text),
    style: {
      fontFamily: '-apple-system, "Hiragino Sans", "Yu Gothic", sans-serif',
      fontSize: FONT_SIZE,
      fill: 0x222233,
      align: "center",
      wordWrap: true,
      wordWrapWidth: 220,
      breakWords: true,
    },
  });

  const w = label.width + PADDING_X * 2;
  const h = label.height + PADDING_Y * 2;

  // 背景
  const bg = new PIXI.Graphics()
    .roundRect(-w / 2, -h, w, h, 6)
    .fill(0xffffff)
    .stroke({ color: 0x000000, width: 1 });
  container.addChild(bg);

  // しっぽ
  const tail = new PIXI.Graphics()
    .moveTo(-5, 0)
    .lineTo(5, 0)
    .lineTo(0, 6)
    .closePath()
    .fill(0xffffff)
    .stroke({ color: 0x000000, width: 1 });
  container.addChild(tail);

  label.anchor.set(0.5, 0);
  label.x = 0;
  label.y = -h + PADDING_Y;
  container.addChild(label);

  // 積み上げ管理
  const list = stacks.get(agent) || [];
  const stackOffset = list.length * (h + STACK_GAP);
  const baseY = charDef.y - 50 - stackOffset;
  container.x = charDef.x;
  container.y = baseY;
  list.push(container);
  stacks.set(agent, list);

  overlayLayer.addChild(container);

  // 初期状態: 縮小 + 透明
  container.alpha = 0;
  container.scale.set(0.6);
  container.rotation = 0;

  // 入場: back.out でバウンス
  gsap.to(container, {
    alpha: 1,
    duration: 0.18,
    ease: "power2.out",
  });
  gsap.to(container.scale, {
    x: 1,
    y: 1,
    duration: 0.32,
    ease: "back.out(1.7)",
  });

  // ジッター (0.45s 目に rotation ±1.5°)
  gsap.to(container, {
    rotation: 0.026,
    duration: 0.18,
    delay: 0.4,
    yoyo: true,
    repeat: 1,
    ease: "sine.inOut",
  });

  // キャラ追従 (歩行中バブルが付いて行く)
  let trackHandle = null;
  if (typeof getPos === "function") {
    trackHandle = (ticker) => {
      const p = getPos();
      if (!p) return;
      // 元の stackOffset を維持しつつキャラに追随
      const idx = list.indexOf(container);
      const off = idx * (h + STACK_GAP);
      container.x = p.x;
      container.y = p.y - 50 - off;
    };
    PIXI.Ticker.shared.add(trackHandle);
  }

  // 退場 (ttlMs 後)
  setTimeout(() => {
    if (trackHandle) PIXI.Ticker.shared.remove(trackHandle);
    gsap.to(container, {
      alpha: 0,
      duration: 0.22,
      ease: "power2.in",
    });
    gsap.to(container.scale, {
      x: 0.85,
      y: 0.85,
      duration: 0.22,
      ease: "power2.in",
      onComplete: () => {
        const arr = stacks.get(agent) || [];
        const i = arr.indexOf(container);
        if (i >= 0) arr.splice(i, 1);
        if (!container.destroyed) container.destroy({ children: true });
      },
    });
  }, ttlMs);
}

function clampText(s) {
  if (!s) return "";
  s = String(s).replace(/\s+/g, " ").trim();
  if (s.length > 60) return s.slice(0, 58) + "…";
  return s;
}
