// PixiJS シーン構築。事務所俯瞰ビュー (床 / 家具 / キャラ / 吹き出し)。
// PixiJS v8 を CDN グローバル PIXI として使う。
// Phase 2: キャラは textures (sprite sheet) があれば AnimatedSprite、なければ Graphics 矩形にフォールバック。

import { CHAR_DEFS, CANVAS_W, CANVAS_H, buildCharacter, isStaff } from "/pixel-static/characters.js";
import { spawnBubble } from "/pixel-static/speech.js";

export async function createScene(rootEl, { onCharClick, textures = null, sazanTextures = null }) {
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

  // 玉座 (サザンの後ろ)
  furniture.addChild(
    new PIXI.Graphics()
      .roundRect(CHAR_DEFS.souther.x - 48, CHAR_DEFS.souther.y - 70, 96, 60, 8)
      .fill({ color: 0x4a3a6e, alpha: 0.85 })
      .stroke({ color: 0xb18cff, width: 2, alpha: 0.7 })
  );

  // 机 (各部下の前 = 下方向)
  ["yuko", "designer", "engineer", "writer"].forEach((id) => {
    const def = CHAR_DEFS[id];
    furniture.addChild(
      new PIXI.Graphics()
        .roundRect(def.x - 42, def.y + 36, 84, 16, 3)
        .fill({ color: 0x3a3450 })
        .stroke({ color: 0x55456a, width: 1 })
    );
  });

  // 部屋の壁
  furniture.addChild(
    new PIXI.Graphics()
      .roundRect(20, 30, CANVAS_W - 40, CANVAS_H - 50, 8)
      .stroke({ color: 0x55456a, width: 2 })
  );

  // 玄関ラベル
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

  // タイトル
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
    // サザンは Phase 2.5 の 36 ポーズ専用シート、他は Phase 2 の 4 ポーズシート
    const ag = agent === "souther" ? sazanTextures : (textures?.[agent] || null);
    const c = buildCharacter(agent, def, onCharClick, ag);
    charLayer.addChild(c);
    charactersById[agent] = c;
  }
  stage.addChild(charLayer);

  // ───────── overlayLayer (吹き出し) ─────────
  const overlay = new PIXI.Container();
  overlay.zIndex = 30;
  overlay.sortableChildren = true;
  stage.addChild(overlay);

  const bubbleStacks = new Map();

  /** scene API: 指定キャラの **現在位置** に吹き出しを出す (歩行中は追随) */
  function bubble(agent, text, ttlMs = 3000) {
    if (!isStaff(agent)) return;
    const c = charactersById[agent];
    const def = CHAR_DEFS[agent];
    // 初期位置はキャラの現在座標 (歩行中なら walking 中の位置)
    const initialPos = c ? { x: c.x, y: c.y } : def;
    const getPos = c ? () => ({ x: c.x, y: c.y }) : null;
    spawnBubble(overlay, initialPos, text, ttlMs, bubbleStacks, agent, getPos);
  }

  return {
    app,
    bubble,
    charactersById,
    destroy: () => app.destroy(true, { children: true }),
  };
}
