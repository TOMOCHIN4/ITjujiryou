// 5キャラの座標・色・絵文字・表示名のマスタテーブル。
// コードID (souther/yuko/...) は DB 側の from_agent / to_agent と一致。
// 表示名 (サザン/ユウコ/...) は Phase 0 で確定した愛帝十字陵 v3.1 仕様。

export const CANVAS_W = 800;
export const CANVAS_H = 600;

export const CHAR_DEFS = {
  souther: {
    name: "サザン",
    role: "CEO・愛帝",
    icon: "👑",
    color: 0xb18cff,
    x: 400, y: 160,  // 中央上 (玉座)
  },
  yuko: {
    name: "ユウコ",
    role: "秘書・COO",
    icon: "💼",
    color: 0xffa3c1,
    x: 200, y: 340,  // 左 (受付)
  },
  designer: {
    name: "トシ",
    role: "デザイナー",
    icon: "🎨",
    color: 0xffd17a,
    x: 560, y: 340,  // 右
  },
  engineer: {
    name: "センシロウ",
    role: "リードエンジニア",
    icon: "🛠",
    color: 0x88d8ff,
    x: 280, y: 480,  // 左下
  },
  writer: {
    name: "ハオウ",
    role: "ライター・コピー部長",
    icon: "✍️",
    color: 0xb6e388,
    x: 480, y: 480,  // 右下
  },
};

export function isStaff(agent) {
  return agent && Object.prototype.hasOwnProperty.call(CHAR_DEFS, agent);
}

/**
 * 1キャラの PIXI.Container を作る。
 *  - textures が渡されれば AnimatedSprite ベース (Phase 2 本素材)
 *  - null なら Graphics 矩形 + 絵文字 にフォールバック (Phase 1 互換)
 *
 * 戻り値の Container には以下が生えている:
 *  - _charId, _agent: agent コードID
 *  - _currentPose: 現在の state (idle / typing / talking / walking)
 *  - setState(pose): state 切替 (textures が無いと no-op)
 *  - _bob: GSAP の idle bob を抑止する停止フック (animation.js から差し込み)
 */
export function buildCharacter(agent, def, onClick, textures = null) {
  const container = new PIXI.Container();
  container.x = def.x;
  container.y = def.y;
  container.zIndex = 20;
  container._charId = agent;
  container._agent = agent;
  container._textures = textures?.[agent] || null;
  container._currentPose = "idle";

  let body;
  const usingSprites = !!container._textures?.idle;

  if (usingSprites) {
    body = new PIXI.AnimatedSprite(container._textures.idle);
    body.anchor.set(0.5, 0.55);
    body.scale.set(0.34);  // 256 -> ~87px
    body.animationSpeed = 0.1;
    body.play();
    container.addChild(body);
  } else {
    // Phase 1 フォールバック: 角丸矩形 + 絵文字
    body = new PIXI.Graphics()
      .roundRect(-18, -18, 36, 36, 6)
      .fill({ color: def.color, alpha: 0.9 })
      .stroke({ color: 0xffffff, width: 1, alpha: 0.4 });
    container.addChild(body);
    const icon = new PIXI.Text({
      text: def.icon,
      style: { fontSize: 24, align: "center" },
    });
    icon.anchor.set(0.5);
    icon.y = -2;
    container.addChild(icon);
  }

  // 表示名ラベル
  const label = new PIXI.Text({
    text: def.name,
    style: {
      fontFamily: '-apple-system, "Hiragino Sans", "Yu Gothic", sans-serif',
      fontSize: 11,
      fill: 0xffffff,
      stroke: { color: 0x000000, width: 3 },
      align: "center",
    },
  });
  label.anchor.set(0.5, 0);
  label.y = usingSprites ? 32 : 22;
  container.addChild(label);

  // クリック領域 (sprite はやや広め)
  container.eventMode = "static";
  container.cursor = "pointer";
  container.hitArea = usingSprites
    ? new PIXI.Rectangle(-36, -50, 72, 90)
    : new PIXI.Rectangle(-26, -26, 52, 60);
  container.on("pointertap", () => onClick(agent));

  container.on("pointerover", () => { body.tint = 0xeeeeff; });
  container.on("pointerout",  () => { body.tint = 0xffffff; });

  // state 切替 (Phase 2)
  container._body = body;
  container.setState = function (pose) {
    if (!this._textures || !this._textures[pose]) return;
    if (this._currentPose === pose) return;
    this._currentPose = pose;
    this._body.textures = this._textures[pose];
    this._body.animationSpeed = pose === "typing" ? 0.18 : 0.1;
    this._body.play();
  };

  return container;
}
