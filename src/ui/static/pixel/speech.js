// 吹き出し (SpeechBubble) — キャラ頭上に一時表示する角丸矩形 + テキスト
// 同じキャラに複数バブルが重ならないよう、上に積み上げてから時間で消える。

const PADDING_X = 8;
const PADDING_Y = 5;
const FONT_SIZE = 12;
const STACK_GAP = 4;

/**
 * 吹き出しを overlayLayer に追加。
 * @param {PIXI.Container} overlayLayer
 * @param {{x:number,y:number}} charDef    キャラ座標
 * @param {string} text                   表示文
 * @param {number} ttlMs                  ms で消える
 * @param {Map<string, Array>} stacks     キャラごとの活きてるバブル配列 (積み上げ管理)
 * @param {string} agent                  キャラID
 */
export function spawnBubble(overlayLayer, charDef, text, ttlMs, stacks, agent) {
  const container = new PIXI.Container();
  container.zIndex = 30;

  // テキスト先に作って計測
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

  // 背景 (白い角丸矩形 + 黒枠)
  const bg = new PIXI.Graphics()
    .roundRect(-w / 2, -h, w, h, 6)
    .fill(0xffffff)
    .stroke({ color: 0x000000, width: 1 });
  container.addChild(bg);

  // 三角しっぽ
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

  // 同じキャラのバブルを積み上げる
  const list = stacks.get(agent) || [];
  const stackOffset = list.length * (h + STACK_GAP);
  container.x = charDef.x;
  container.y = charDef.y - 30 - stackOffset;
  list.push(container);
  stacks.set(agent, list);

  overlayLayer.addChild(container);

  // フェード in
  container.alpha = 0;
  let inT = 0;
  const fadeIn = (ticker) => {
    inT += ticker.deltaMS;
    container.alpha = Math.min(1, inT / 150);
    if (container.alpha >= 1) PIXI.Ticker.shared.remove(fadeIn);
  };
  PIXI.Ticker.shared.add(fadeIn);

  // ttl 後にフェード out → destroy
  setTimeout(() => {
    let outT = 0;
    const fadeOut = (ticker) => {
      outT += ticker.deltaMS;
      container.alpha = Math.max(0, 1 - outT / 250);
      if (container.alpha <= 0) {
        PIXI.Ticker.shared.remove(fadeOut);
        const arr = stacks.get(agent) || [];
        const idx = arr.indexOf(container);
        if (idx >= 0) arr.splice(idx, 1);
        if (!container.destroyed) container.destroy({ children: true });
      }
    };
    PIXI.Ticker.shared.add(fadeOut);
  }, ttlMs);
}

function clampText(s) {
  if (!s) return "";
  s = String(s).replace(/\s+/g, " ").trim();
  if (s.length > 60) return s.slice(0, 58) + "…";
  return s;
}
