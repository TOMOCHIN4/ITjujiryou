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
    x: 400, y: 140,  // 中央上 (玉座)
  },
  yuko: {
    name: "ユウコ",
    role: "秘書・COO",
    icon: "💼",
    color: 0xffa3c1,
    x: 200, y: 320,  // 左 (受付)
  },
  designer: {
    name: "トシ",
    role: "デザイナー",
    icon: "🎨",
    color: 0xffd17a,
    x: 560, y: 320,  // 右
  },
  engineer: {
    name: "センシロウ",
    role: "リードエンジニア",
    icon: "🛠",
    color: 0x88d8ff,
    x: 280, y: 460,  // 左下
  },
  writer: {
    name: "ハオウ",
    role: "ライター・コピー部長",
    icon: "✍️",
    color: 0xb6e388,
    x: 480, y: 460,  // 右下
  },
};

export function isStaff(agent) {
  return agent && Object.prototype.hasOwnProperty.call(CHAR_DEFS, agent);
}

/**
 * 1キャラの PIXI.Container を作る。32x32 の角丸矩形 + 絵文字 + 表示名ラベル。
 * 戻り値の `_charId` でコードIDを保持し、クリック時にその ID で onClick を呼ぶ。
 */
export function buildCharacter(agent, def, onClick) {
  const container = new PIXI.Container();
  container.x = def.x;
  container.y = def.y;
  container.zIndex = 20;
  container._charId = agent;

  // 体 (角丸矩形)
  const body = new PIXI.Graphics()
    .roundRect(-18, -18, 36, 36, 6)
    .fill({ color: def.color, alpha: 0.9 })
    .stroke({ color: 0xffffff, width: 1, alpha: 0.4 });
  container.addChild(body);

  // 絵文字 (頭部)
  const icon = new PIXI.Text({
    text: def.icon,
    style: { fontSize: 24, align: "center" },
  });
  icon.anchor.set(0.5);
  icon.y = -2;
  container.addChild(icon);

  // 表示名ラベル (下)
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
  label.y = 22;
  container.addChild(label);

  // クリック領域 (キャラ周辺余裕を持たせる)
  container.eventMode = "static";
  container.cursor = "pointer";
  container.hitArea = new PIXI.Rectangle(-26, -26, 52, 60);
  container.on("pointertap", () => onClick(agent));

  // ホバー演出
  container.on("pointerover", () => { body.tint = 0xeeeeff; });
  container.on("pointerout",  () => { body.tint = 0xffffff; });

  return container;
}
