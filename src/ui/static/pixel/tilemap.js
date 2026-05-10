// Phase 3.0 NES topdown RPG: タイル定数・マップデータ・座標変換のシングルソース。
// scene.js / movement.js / characters.js から参照される。

export const TILE_SIZE = 64;
export const MAP_COLS = 16;
export const MAP_ROWS = 12;
export const STAGE_SCALE = 0.75;

// canvas 800x600 内に 論理 1024x768 を 0.75x で描画 = 768x576。レターボックス上下左右 16/12 黒。
// 16-bit SNES テイスト (asset-maker 生成) 用に TILE_SIZE 32→64 へ拡大。STAGE_SCALE で従来と同じ表示サイズ維持。
export const STAGE_OFFSET_X = 16;
export const STAGE_OFFSET_Y = 12;

// タイル ID 体系
export const TILE = {
  FLOOR_A: 0, FLOOR_B: 1,
  WALL_TOP: 2, WALL_SIDE: 3,
  THRONE_TOP: 4, THRONE_BOTTOM: 5,
  DESK_YUKO: 6, DESK_WRITER: 7, DESK_DESIGNER: 8, DESK_ENGINEER: 9,
  COUNTER: 10, DOOR: 11, PLANT: 12, DOCS: 13, RUG: 14, EMPTY: 15,
};

// id → タイルセットファイル名 (spriteLoader が解決)
export const TILE_NAME = {
  0: "floor_carpet_a", 1: "floor_carpet_b",
  2: "wall_top", 3: "wall_side",
  4: "throne_top", 5: "throne_bottom",
  6: "desk_yuko", 7: "desk_writer", 8: "desk_designer", 9: "desk_engineer",
  10: "counter_reception", 11: "door", 12: "plant",
  13: "document_pile", 14: "rug_red", 15: "_empty",
};

const WALKABLE = {
  [TILE.FLOOR_A]: true, [TILE.FLOOR_B]: true,
  [TILE.WALL_TOP]: false, [TILE.WALL_SIDE]: false,
  [TILE.THRONE_TOP]: false, [TILE.THRONE_BOTTOM]: false,
  [TILE.DESK_YUKO]: false, [TILE.DESK_WRITER]: false,
  [TILE.DESK_DESIGNER]: false, [TILE.DESK_ENGINEER]: false,
  [TILE.COUNTER]: false, [TILE.DOOR]: true,
  [TILE.PLANT]: false, [TILE.DOCS]: false,
  [TILE.RUG]: true, [TILE.EMPTY]: true,
};

export function isWalkable(tileId) {
  return WALKABLE[tileId] === true;
}

// 16 cols × 12 rows のオフィスマップ (v4.2: 全面床、壁タイル排除)
// 背景は 1 枚絵 (sprites/background/office.png) で表現するため、MAP は全 0 で walkable に統一。
// 凡例: 0=床A, 1=床B, 2=壁上 (未使用), 3=壁側 (未使用)
export const MAP = [
  [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
  [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
  [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
  [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
  [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
  [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
  [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
  [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
  [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
  [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
  [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
  [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
];

export function tileAt(tx, ty) {
  // CHAR_HOME_TILE / DESK_PLACEMENT は小数 (例: 2.8) を取りうるので必ず floor する。
  const ix = Math.floor(tx);
  const iy = Math.floor(ty);
  if (iy < 0 || iy >= MAP_ROWS || ix < 0 || ix >= MAP_COLS) return TILE.WALL_SIDE;
  return MAP[iy][ix];
}

// キャラの home tile (ピクセル座標は tileToCharX/Y で変換)
// v4.2 整地レイアウト: サザン/三兄弟をより中段寄りに圧縮、左右の正中は tx=7.5 (= MAP_COLS/2)
export const CHAR_HOME_TILE = {
  souther:  { tx: 7.5, ty: 2.8 }, // 上段正中央 (CEO)
  yuko:     { tx: 7.5, ty: 5.5 }, // 中段正中央 (秘書)
  writer:   { tx: 3,   ty: 8.5 }, // 下段左 (ハオウ) ← 0.5 下
  designer: { tx: 7.5, ty: 8.5 }, // 下段正中央 (トシ) ← 0.5 下
  engineer: { tx: 12,  ty: 8.5 }, // 下段右 (センシロウ) ← 0.5 下
};

// 壁の装飾配置 (社訓額縁などのフラットな絵)。anchor は中心、cx/cy は tile 中心、w/h はタイル数。
export const DECOR_PLACEMENT = {
  motto_plaque: { cx: 7.5, cy: 0.75, w: 7.06, h: 1.5 },  // サザン背後の奥壁中央 (上広い台形 452x96)
};

// デスクの配置情報。各キャラの home_tile を中心に w*h タイル分のスペースに展開。
// y_offset = キャラ足元から何 px 上にデスク中心を置くか (下半身を隠す効果)。
// v4.3+ デスク再設計: 我々から見ると裏面 (化粧板側)、キャラ側が正面 (knee well)。
//   souther: 6×2 化粧板 + ワイングラス (バロック・マホガニー)
//   yuko:    6×3 U 字秘書デスク (白大理石 + クローム、サザンと対照)
//   三兄弟:  3×2 スタイリッシュモダン (白大理石 + クローム、ユウコ系で 3 人同一デザイン)
//            asset-maker で 3x3 グリッド一括生成 (desks_brothers_v5.yaml) → 同一フレームで小物のみ差別化:
//              作家 (ハオウ/ラオウ転生): 黒い馬フィギュア + 原稿 + インク + 万年筆 + 革ノート
//              デザイナー (トシ/トキ転生): ペンタブ + スケッチパッド + 多肉植物 + 漢方瓶 + 緑茶マグ
//              エンジニア (センシロウ/ケンシロウ転生): モニタ + ユリア人形 + メカキーボード + 技術書 + コーヒー
export const DESK_PLACEMENT = {
  souther:  { cx: 7.5, cy: 2.8, w: 6, h: 2, y_offset: 0 },
  yuko:     { cx: 7.5, cy: 5.5, w: 6, h: 3, y_offset: 0 },
  writer:   { cx: 3,   cy: 8.5, w: 3, h: 1.5, y_offset: 0 },
  designer: { cx: 7.5, cy: 8.5, w: 3, h: 1.5, y_offset: 0 },
  engineer: { cx: 12,  cy: 8.5, w: 3, h: 1.5, y_offset: 0 },
};

// 座標変換
export const tileToPx = (tx) => tx * TILE_SIZE;
export const tileToPy = (ty) => ty * TILE_SIZE;
// キャラ用: タイル中央下寄り (anchor (0.5, 0.85) と組み合わせて足元中央)
export const tileToCharX = (tx) => tx * TILE_SIZE + TILE_SIZE / 2;
export const tileToCharY = (ty) => ty * TILE_SIZE + TILE_SIZE - 2;
