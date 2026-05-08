// PixiJS シーン構築。事務所俯瞰ビュー (床 / 家具 / キャラ / 吹き出し)。
// PixiJS v8.6 を CDN から読み込み、グローバル PIXI を使う。

import { CHAR_DEFS, CANVAS_W, CANVAS_H, buildCharacter, isStaff } from "/pixel-static/characters.js";
import { spawnBubble } from "/pixel-static/speech.js";

export async function createScene(rootEl, { onCharClick }) {
  const app = new PIXI.Application();
  await app.init({
    width: CANVAS_W,
    height: CANVAS_H,
    background: 0x2a2438,
    antialias: false,
  });
  rootEl.appendChild(app.canvas);

  const stage = app.stage;
  stage.sortableChildren = true;

  // ───────── floorLayer (チェッカー床) ─────────
  const floor = new PIXI.Container();
  floor.zIndex = 0;
  const tile = 16;
  const cols = Math.ceil(CANVAS_W / tile);
  const rows = Math.ceil(CANVAS_H / tile);
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      const dark = (r + c) % 2 === 0;
      floor.addChild(
        new PIXI.Graphics()
          .rect(c * tile, r * tile, tile, tile)
          .fill(dark ? 0x252033 : 0x2c263d)
      );
    }
  }
  stage.addChild(floor);

  // ───────── furnitureLayer ─────────
  const furniture = new PIXI.Container();
  furniture.zIndex = 10;

  // 玉座 (souther の後ろ)
  furniture.addChild(
    new PIXI.Graphics()
      .roundRect(CHAR_DEFS.souther.x - 40, CHAR_DEFS.souther.y - 60, 80, 50, 8)
      .fill({ color: 0x4a3a6e, alpha: 0.85 })
      .stroke({ color: 0xb18cff, width: 2, alpha: 0.7 })
  );

  // 机 (各部下の前 = 下方向)
  ["yuko", "designer", "engineer", "writer"].forEach((id) => {
    const def = CHAR_DEFS[id];
    furniture.addChild(
      new PIXI.Graphics()
        .roundRect(def.x - 36, def.y + 22, 72, 14, 3)
        .fill({ color: 0x3a3450 })
        .stroke({ color: 0x55456a, width: 1 })
    );
  });

  // 部屋の壁 (枠)
  furniture.addChild(
    new PIXI.Graphics()
      .roundRect(20, 30, CANVAS_W - 40, CANVAS_H - 50, 8)
      .stroke({ color: 0x55456a, width: 2 })
  );

  // 玄関ラベル (左下)
  const door = new PIXI.Graphics()
    .roundRect(30, CANVAS_H - 60, 60, 28, 4)
    .fill({ color: 0x1a1525 })
    .stroke({ color: 0x6e5d8a, width: 1 });
  furniture.addChild(door);
  const doorLabel = new PIXI.Text({
    text: "🚪 受付",
    style: {
      fontFamily: '-apple-system, "Hiragino Sans", "Yu Gothic", sans-serif',
      fontSize: 11,
      fill: 0xa09cc0,
    },
  });
  doorLabel.anchor.set(0, 0.5);
  doorLabel.x = 36;
  doorLabel.y = CANVAS_H - 46;
  furniture.addChild(doorLabel);

  // タイトル (上中央)
  const title = new PIXI.Text({
    text: "愛帝十字陵 — 7F オフィス",
    style: {
      fontFamily: '-apple-system, "Hiragino Sans", "Yu Gothic", sans-serif',
      fontSize: 12,
      fill: 0x8a82a8,
      letterSpacing: 1,
    },
  });
  title.anchor.set(0.5, 0);
  title.x = CANVAS_W / 2;
  title.y = 8;
  furniture.addChild(title);

  stage.addChild(furniture);

  // ───────── characterLayer ─────────
  const charLayer = new PIXI.Container();
  charLayer.zIndex = 20;
  charLayer.sortableChildren = true;
  const charactersById = {};
  for (const [agent, def] of Object.entries(CHAR_DEFS)) {
    const c = buildCharacter(agent, def, onCharClick);
    charLayer.addChild(c);
    charactersById[agent] = c;
  }
  stage.addChild(charLayer);

  // ───────── overlayLayer (吹き出し) ─────────
  const overlay = new PIXI.Container();
  overlay.zIndex = 30;
  overlay.sortableChildren = true;
  stage.addChild(overlay);

  // バブル積み上げ管理
  const bubbleStacks = new Map();

  /** scene API: 指定キャラの頭上に吹き出しを表示 */
  function bubble(agent, text, ttlMs = 3000) {
    if (!isStaff(agent)) return; // クライアントや system は無視
    const def = CHAR_DEFS[agent];
    spawnBubble(overlay, def, text, ttlMs, bubbleStacks, agent);
  }

  /** 一時的にキャラを発光 (現在は未使用、Phase 2 で歩行アニメ等に拡張可) */
  function pulse(agent) {
    const c = charactersById[agent];
    if (!c) return;
    let t = 0;
    const fn = (ticker) => {
      t += ticker.deltaMS;
      c.scale.set(1 + Math.sin(t / 80) * 0.04);
      if (t > 600) {
        c.scale.set(1);
        PIXI.Ticker.shared.remove(fn);
      }
    };
    PIXI.Ticker.shared.add(fn);
  }

  return {
    app,
    bubble,
    pulse,
    destroy: () => app.destroy(true, { children: true }),
  };
}
