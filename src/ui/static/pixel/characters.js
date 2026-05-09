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
    x: 400, y: 160,
  },
  yuko: {
    name: "ユウコ",
    role: "秘書・COO",
    icon: "💼",
    color: 0xffa3c1,
    x: 200, y: 340,
  },
  designer: {
    name: "トシ",
    role: "デザイナー",
    icon: "🎨",
    color: 0xffd17a,
    x: 560, y: 340,
  },
  engineer: {
    name: "センシロウ",
    role: "リードエンジニア",
    icon: "🛠",
    color: 0x88d8ff,
    x: 280, y: 480,
  },
  writer: {
    name: "ハオウ",
    role: "ライター・コピー部長",
    icon: "✍️",
    color: 0xb6e388,
    x: 480, y: 480,
  },
};

export function isStaff(agent) {
  return agent && Object.prototype.hasOwnProperty.call(CHAR_DEFS, agent);
}

// state ごとの推奨アニメーション速度 (PIXI.AnimatedSprite.animationSpeed)。
// 60Hz tick × value が実 fps。例: 0.1 = 6fps。
const POSE_ANIM_SPEED = {
  idle:    0.044,  // 8 frame × ~3 秒 (slow breath)
  walking: 0.18,   // 8 frame × ~0.45 秒 (滑らかな歩行)
  talking: 0.13,   // 4 frame × ~0.5 秒 (mouth flap)
  typing:  0.18,   // 旧 staff 用
};

/**
 * 1キャラの PIXI.Container を作る。
 *  - agentTextures が渡されれば AnimatedSprite ベース
 *  - null なら Graphics 矩形 + 絵文字 にフォールバック (Phase 1 互換)
 *
 * agentTextures の形:
 *  { idle: [Texture, ...], walking: [Texture, ...], talking: [Texture, ...],
 *    [其他 pose 名]: [Texture] }   (1 要素配列の static pose も可)
 *
 * 戻り値 Container に生える API:
 *  - _charId, _agent: agent コードID
 *  - _currentPose: 現在の pose 名
 *  - setState(pose): pose 切替 (texture array を差し替えて再生)。当該 pose の texture が無ければ no-op
 *  - _spriteScale: ヒットエリア計算用、外部からは触らない
 */
export function buildCharacter(agent, def, onClick, agentTextures = null) {
  const container = new PIXI.Container();
  container.x = def.x;
  container.y = def.y;
  container.zIndex = 20;
  container._charId = agent;
  container._agent = agent;
  container._textures = agentTextures || null;
  container._currentPose = "idle";

  let body;
  const usingSprites = !!agentTextures?.idle;

  if (usingSprites) {
    body = new PIXI.AnimatedSprite(agentTextures.idle);
    body.anchor.set(0.5, 0.55);
    // サザンのみ大きめスケール (玉座があるため少し縦長になりがち)
    body.scale.set(agent === "souther" ? 0.36 : 0.34);
    body.animationSpeed = POSE_ANIM_SPEED.idle;
    body.loop = true;
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
  label.y = usingSprites ? 36 : 22;
  container.addChild(label);

  // クリック領域
  container.eventMode = "static";
  container.cursor = "pointer";
  container.hitArea = usingSprites
    ? new PIXI.Rectangle(-40, -55, 80, 100)
    : new PIXI.Rectangle(-26, -26, 52, 60);
  container.on("pointertap", () => onClick(agent));

  container.on("pointerover", () => { body.tint = 0xeeeeff; });
  container.on("pointerout",  () => { body.tint = 0xffffff; });

  // state 切替 API
  container._body = body;
  container.setState = function (pose) {
    if (!this._textures || !this._textures[pose]) return;
    if (this._currentPose === pose) return;
    this._currentPose = pose;
    this._body.textures = this._textures[pose];
    this._body.animationSpeed = POSE_ANIM_SPEED[pose] ?? 0.1;
    this._body.gotoAndPlay(0);
  };

  return container;
}
