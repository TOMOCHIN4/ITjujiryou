// Phase 3.0 NES topdown: 5キャラのマスタテーブル + buildCharacter (4方向 walk + idle)。
// 座標は tilemap.js の CHAR_HOME_TILE が source of truth。CHAR_DEFS は表示メタのみ。

import { CHAR_HOME_TILE, tileToCharX, tileToCharY } from "/pixel-static/tilemap.js";

export const CANVAS_W = 800;
export const CANVAS_H = 600;

export const CHAR_DEFS = {
  souther:  { name: "サザン",     role: "CEO・愛帝",         icon: "👑", color: 0xb18cff },
  yuko:     { name: "ユウコ",     role: "秘書・COO",          icon: "💼", color: 0xffa3c1 },
  designer: { name: "トシ",       role: "デザイナー",         icon: "🎨", color: 0xffd17a },
  engineer: { name: "センシロウ", role: "リードエンジニア",   icon: "🛠", color: 0x88d8ff },
  writer:   { name: "ハオウ",     role: "ライター・コピー部長", icon: "✍️", color: 0xb6e388 },
};

export function isStaff(agent) {
  return agent && Object.prototype.hasOwnProperty.call(CHAR_DEFS, agent);
}

// 60Hz × 0.15 = 9fps、2 フレーム cycle ≈ 0.22 秒/周。tile-step 0.18 秒とほぼ同期。
const WALK_SPEED = 0.15;

const FACINGS = ["down", "up", "left", "right"];

/**
 * agentTextures = { down:[Texture, Texture], up:[..], left:[..], right:[..] }
 * 各 facing は 2 frame walk アニメ。idle は frame[0] で gotoAndStop。
 *
 * setState(state, facing):
 *   state ∈ {"idle", "walking"}
 *   facing ∈ {"down", "up", "left", "right"}
 */
export function buildCharacter(agent, def, onClick, agentTextures = null) {
  const home = CHAR_HOME_TILE[agent];
  const container = new PIXI.Container();
  container.x = tileToCharX(home.tx);
  container.y = tileToCharY(home.ty);
  container.zIndex = 20 + container.y;
  container._charId = agent;
  container._agent = agent;
  container._textures = agentTextures || null;
  container._currentState = "idle";
  container._facing = "down";

  let body;
  const usingSprites = !!agentTextures?.down;

  if (usingSprites) {
    body = new PIXI.AnimatedSprite(agentTextures.down);
    body.anchor.set(0.5, 0.85);
    body.scale.set(1.0);
    body.animationSpeed = 0;
    body.loop = true;
    body.gotoAndStop(0);
    container.addChild(body);
  } else {
    // フォールバック: 24x28 角丸矩形 + 絵文字 (テクスチャロード失敗時の縮退)
    body = new PIXI.Graphics()
      .roundRect(-12, -22, 24, 28, 4)
      .fill({ color: def.color, alpha: 0.9 })
      .stroke({ color: 0xffffff, width: 1, alpha: 0.5 });
    container.addChild(body);
    const icon = new PIXI.Text({ text: def.icon, style: { fontSize: 16 } });
    icon.anchor.set(0.5);
    icon.y = -10;
    container.addChild(icon);
  }

  // 名前ラベル (ピクセルフォント風、頭上)
  const label = new PIXI.Text({
    text: def.name,
    style: {
      fontFamily: '"Hiragino Sans", "Yu Gothic", monospace',
      fontSize: 9,
      fill: 0xffffff,
      stroke: { color: 0x000000, width: 2 },
      align: "center",
    },
  });
  label.anchor.set(0.5, 1);
  label.y = -28;
  container.addChild(label);

  container.eventMode = "static";
  container.cursor = "pointer";
  container.hitArea = new PIXI.Rectangle(-16, -32, 32, 36);
  container.on("pointertap", () => onClick(agent));
  container.on("pointerover", () => { body.tint = 0xddddff; });
  container.on("pointerout",  () => { body.tint = 0xffffff; });

  container._body = body;
  container.setState = function (state, facing) {
    facing = facing || this._facing || "down";
    if (!FACINGS.includes(facing)) facing = "down";
    if (this._currentState === state && this._facing === facing) return;
    this._currentState = state;
    this._facing = facing;
    if (!this._textures?.[facing]) return;
    this._body.textures = this._textures[facing];
    if (state === "walking") {
      this._body.animationSpeed = WALK_SPEED;
      this._body.gotoAndPlay(0);
    } else {
      this._body.animationSpeed = 0;
      this._body.gotoAndStop(0);
    }
  };

  return container;
}
