// Phase 3.0 NES topdown RPG: タイル定数・マップデータ・座標変換のシングルソース。
// scene.js / movement.js / characters.js から参照される。

export const TILE_SIZE = 32;
export const MAP_COLS = 16;
export const MAP_ROWS = 12;
export const STAGE_SCALE = 1.5;

// canvas 800x600 内に 論理 512x384 を 1.5x で描画 = 768x576。レターボックス上下左右 16/12 黒。
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

// 16 cols × 12 rows のオフィスマップ
// 凡例: 0=床A, 2=壁上, 3=壁側, 4=玉座背, 5=玉座座面, 6-9=各机, 10=受付, 11=ドア, 12=植物, 13=書類, 14=赤絨毯
export const MAP = [
  // ty=0: 上壁
  [2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2],
  // ty=1: 玉座背 (7,1)
  [3,0,0,0,0,0,0,4,0,0,0,0,0,0,0,3],
  // ty=2: 玉座座面 (7,2)
  [3,0,0,0,0,0,0,5,0,0,0,0,0,0,0,3],
  // ty=3: 玉座前赤絨毯 (6-8,3) ← サザン立位置 (7,3)
  [3,0,0,0,0,0,14,14,14,0,0,0,0,0,0,3],
  // ty=4: 中通路
  [3,0,0,0,0,0,0,0,0,0,0,0,0,0,0,3],
  // ty=5: ユウコ机 (4,5) と ハオウ机 (11,5)、両端に植物
  [3,0,12,0,6,0,0,0,0,0,0,7,0,12,0,3],
  // ty=6: ユウコ立位置 (5,6) とハオウ立位置 (10,6)
  [3,0,0,0,0,0,0,0,0,0,0,0,0,0,0,3],
  // ty=7: 通路
  [3,1,0,0,0,0,0,0,0,0,0,0,0,0,1,3],
  // ty=8: トシ机 (3,8) と センシロウ机 (12,8)
  [3,0,0,8,0,0,0,0,0,0,0,0,9,0,0,3],
  // ty=9: トシ立位置 (4,9) と センシロウ立位置 (11,9)
  [3,0,0,0,0,0,0,0,0,0,0,0,0,0,0,3],
  // ty=10: 受付カウンタ (2,10) + 書類 (3,10)(4,10)
  [3,0,10,13,13,0,0,0,0,0,0,0,0,0,0,3],
  // ty=11: ドア (1,11) + 下壁
  [3,11,2,2,2,2,2,2,2,2,2,2,2,2,2,3],
];

export function tileAt(tx, ty) {
  if (ty < 0 || ty >= MAP_ROWS || tx < 0 || tx >= MAP_COLS) return TILE.WALL_SIDE;
  return MAP[ty][tx];
}

// キャラの home tile (ピクセル座標は tileToCharX/Y で変換)
export const CHAR_HOME_TILE = {
  souther:  { tx: 7,  ty: 3 },   // 玉座下の赤絨毯
  yuko:     { tx: 5,  ty: 6 },   // ユウコ机 (4,5) の右下
  writer:   { tx: 10, ty: 6 },   // ハオウ机 (11,5) の左下
  designer: { tx: 4,  ty: 9 },   // トシ机 (3,8) の右下
  engineer: { tx: 11, ty: 9 },   // センシロウ机 (12,8) の左下
};

// 座標変換
export const tileToPx = (tx) => tx * TILE_SIZE;
export const tileToPy = (ty) => ty * TILE_SIZE;
// キャラ用: タイル中央下寄り (anchor (0.5, 0.85) と組み合わせて足元中央)
export const tileToCharX = (tx) => tx * TILE_SIZE + TILE_SIZE / 2;
export const tileToCharY = (ty) => ty * TILE_SIZE + TILE_SIZE - 2;
