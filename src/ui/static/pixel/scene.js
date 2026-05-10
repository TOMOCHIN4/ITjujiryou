// Phase 3.0 NES topdown シーン構築。
// PixiJS v8 グローバル PIXI を CDN から使用。tilemap.js のマップを走査してタイル + キャラ + 吹き出しを配置。
// stage.scale.set(1.5) で論理 512x384 を 768x576 表示、canvas 800x600 内にレターボックス中央配置。

import { CHAR_DEFS, buildCharacter, isStaff, CANVAS_W, CANVAS_H } from "/pixel-static/characters.js";
import { spawnBubble } from "/pixel-static/speech.js";
import { mountEmailPopupLayer } from "/pixel-static/emailPopup.js";
import {
  TILE_SIZE, MAP_COLS, MAP_ROWS, MAP, tileAt, TILE_NAME, TILE,
  STAGE_SCALE, STAGE_OFFSET_X, STAGE_OFFSET_Y, tileToPx, tileToPy,
  DESK_PLACEMENT, DECOR_PLACEMENT,
} from "/pixel-static/tilemap.js";

export async function createScene(rootEl, { onCharClick, charTextures = null, tileTextures = null, deskTextures = null, backgroundTexture = null, decorTextures = null }) {
  const app = new PIXI.Application();
  await app.init({
    width: CANVAS_W,
    height: CANVAS_H,
    background: 0x000000,
    antialias: false,
    roundPixels: true,
  });
  rootEl.appendChild(app.canvas);

  const stage = app.stage;
  stage.sortableChildren = true;
  stage.x = STAGE_OFFSET_X;
  stage.y = STAGE_OFFSET_Y;
  stage.scale.set(STAGE_SCALE);

  // ───────── backgroundLayer (オフィス全体を 1 枚絵で敷く) ─────────
  const floor = new PIXI.Container();
  floor.zIndex = 0;
  if (backgroundTexture) {
    const bg = new PIXI.Sprite(backgroundTexture);
    bg.x = 0;
    bg.y = 0;
    bg.width = MAP_COLS * TILE_SIZE;
    bg.height = MAP_ROWS * TILE_SIZE;
    floor.addChild(bg);
  } else {
    // フォールバック: 暗紫タイル (背景画像読み込み失敗時)
    for (let ty = 0; ty < MAP_ROWS; ty++) {
      for (let tx = 0; tx < MAP_COLS; tx++) {
        const dark = (tx + ty) % 2 === 0;
        floor.addChild(
          new PIXI.Graphics()
            .rect(tileToPx(tx), tileToPy(ty), TILE_SIZE, TILE_SIZE)
            .fill(dark ? 0x252033 : 0x2c263d)
        );
      }
    }
  }
  stage.addChild(floor);

  // ───────── furnitureLayer (壁・玉座・机・受付・植物・書類・赤絨毯) ─────────
  const furniture = new PIXI.Container();
  furniture.zIndex = 10;
  furniture.sortableChildren = true;

  for (let ty = 0; ty < MAP_ROWS; ty++) {
    for (let tx = 0; tx < MAP_COLS; tx++) {
      const id = tileAt(tx, ty);
      if (id === TILE.FLOOR_A || id === TILE.FLOOR_B || id === TILE.EMPTY) continue;
      const name = TILE_NAME[id];
      const tex = tileTextures?.[name];
      if (!tex) continue;
      const s = new PIXI.Sprite(tex);
      s.x = tileToPx(tx);
      s.y = tileToPy(ty);
      s.width = TILE_SIZE;
      s.height = TILE_SIZE;
      // y-sort: 家具とキャラを y で重ね合わせ。家具は base 10 + y/16 (キャラ 20 + y より下になる)
      s.zIndex = 10 + s.y;
      furniture.addChild(s);
    }
  }
  stage.addChild(furniture);

  // ───────── decorLayer (壁装飾: 社訓額縁など) ─────────
  const decor = new PIXI.Container();
  decor.zIndex = 5;  // 背景 (0) より上、キャラ (20+) より下
  for (const [name, place] of Object.entries(DECOR_PLACEMENT)) {
    const tex = decorTextures?.[name];
    if (!tex) continue;
    const s = new PIXI.Sprite(tex);
    s.anchor.set(0.5, 0.5);
    s.x = place.cx * TILE_SIZE + TILE_SIZE / 2;
    s.y = place.cy * TILE_SIZE + TILE_SIZE / 2;
    s.width = place.w * TILE_SIZE;
    s.height = place.h * TILE_SIZE;
    decor.addChild(s);
  }
  stage.addChild(decor);

  // ───────── characterLayer ─────────
  const charLayer = new PIXI.Container();
  charLayer.zIndex = 20;
  charLayer.sortableChildren = true;
  const charactersById = {};
  for (const [agent, def] of Object.entries(CHAR_DEFS)) {
    const tex = charTextures?.[agent] || null;
    const c = buildCharacter(agent, def, onCharClick, tex);
    charLayer.addChild(c);
    charactersById[agent] = c;
  }
  // デスクをキャラより前面に配置 (下半身が隠れて「座っている」演出)
  for (const [agent, place] of Object.entries(DESK_PLACEMENT)) {
    const tex = deskTextures?.[agent];
    if (!tex) continue;
    const s = new PIXI.Sprite(tex);
    s.anchor.set(0.5, 0.5);
    s.x = place.cx * TILE_SIZE + TILE_SIZE / 2;
    // キャラの足元 = cy * TILE + TILE - 2、そこから y_offset 上にデスク中心
    s.y = place.cy * TILE_SIZE + TILE_SIZE - 2 - place.y_offset;
    s.width = place.w * TILE_SIZE;
    s.height = place.h * TILE_SIZE;
    // y-sort: キャラの zIndex (20 + container.y) より +20 でデスクを前面に
    s.zIndex = 20 + s.y + 20;
    charLayer.addChild(s);
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
    if (!c) return;
    const initialPos = { x: c.x, y: c.y };
    const getPos = () => ({ x: c.x, y: c.y });
    spawnBubble(overlay, initialPos, text, ttlMs, bubbleStacks, agent, getPos);
  }

  // ───────── メール popup overlay (HTML、canvas の上の右上に積む) ─────────
  const emailLayer = mountEmailPopupLayer(rootEl);

  return {
    app,
    bubble,
    emailPopup: emailLayer.show,
    charactersById,
    destroy: () => {
      emailLayer.destroy();
      app.destroy(true, { children: true });
    },
  };
}
