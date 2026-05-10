// 吹き出し (SpeechBubble) — GSAP 連動。
// 入場: scale 0 → 1 with back.out, alpha 0 → 1
// 滞在: 0.4s 目に yoyo jitter (rotation ±3°)
// 退場: scale → 0.85, alpha → 0 with power2.in
// 視認性: drop shadow + 2px 黒外枠 + キャラ色アクセントバー + bold 13px

import gsap from "https://cdn.jsdelivr.net/npm/gsap@3.12.5/+esm";
import { CHAR_DEFS } from "/pixel-static/characters.js";

const PADDING_X = 9;
const PADDING_Y = 6;
const FONT_SIZE = 13;
const STACK_GAP = 4;
const SHADOW_OFFSET = 2;
const ACCENT_HEIGHT = 3;

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
  container.zIndex = 100;  // overlay 全体の中で最上位に
  container.pivot.set(0, 0);

  const accentColor = CHAR_DEFS[agent]?.color ?? 0xb18cff;

  const label = new PIXI.Text({
    text: clampText(text),
    style: {
      fontFamily: '-apple-system, "Hiragino Sans", "Yu Gothic", sans-serif',
      fontSize: FONT_SIZE,
      fontWeight: "bold",
      fill: 0x1c1830,
      align: "center",
      wordWrap: true,
      wordWrapWidth: 220,
      breakWords: true,
    },
  });

  const w = label.width + PADDING_X * 2;
  const h = label.height + PADDING_Y * 2;

  // ドロップシャドウ (背景を 2px 右下にずらした半透明黒)
  const shadow = new PIXI.Graphics()
    .roundRect(-w / 2 + SHADOW_OFFSET, -h + SHADOW_OFFSET, w, h, 6)
    .fill({ color: 0x000000, alpha: 0.35 });
  container.addChild(shadow);

  // 背景 (白 + 太い黒外枠)
  const bg = new PIXI.Graphics()
    .roundRect(-w / 2, -h, w, h, 6)
    .fill(0xffffff)
    .stroke({ color: 0x000000, width: 2 });
  container.addChild(bg);

  // 上端のキャラ色アクセントバー
  const accent = new PIXI.Graphics()
    .roundRect(-w / 2 + 3, -h + 3, w - 6, ACCENT_HEIGHT, 1.5)
    .fill(accentColor);
  container.addChild(accent);

  // しっぽ (吹き出しの下)
  const tail = new PIXI.Graphics()
    .moveTo(-6, 0)
    .lineTo(6, 0)
    .lineTo(0, 7)
    .closePath()
    .fill(0xffffff)
    .stroke({ color: 0x000000, width: 2 });
  container.addChild(tail);

  label.anchor.set(0.5, 0);
  label.x = 0;
  label.y = -h + PADDING_Y + 1;  // accent バー分だけ下げる
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

  // ジッター (0.4s 目に rotation ±3°、視線を引き寄せる)
  gsap.to(container, {
    rotation: 0.052,
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
