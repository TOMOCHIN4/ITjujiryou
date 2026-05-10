// 座標変換とマップ範囲の単一の真実。背景は 1 枚絵で表現するため、タイル絵は持たず
// 「歩ける床 (0) と範囲外 (-1)」の 2 値だけを扱う。movement.js の BFS 用。

export const TILE_SIZE = 64;
export const MAP_COLS = 16;
export const MAP_ROWS = 12;
export const STAGE_SCALE = 0.75;

// canvas 800x600 内に 論理 1024x768 を 0.75x で描画 = 768x576。レターボックス上下左右 16/12 黒。
export const STAGE_OFFSET_X = 16;
export const STAGE_OFFSET_Y = 12;

const FLOOR = 0;
const OOB = -1;

export function tileAt(tx, ty) {
  // CHAR_HOME_TILE / DESK_PLACEMENT は小数 (例: 2.8) を取りうるので必ず floor する。
  const ix = Math.floor(tx);
  const iy = Math.floor(ty);
  if (iy < 0 || iy >= MAP_ROWS || ix < 0 || ix >= MAP_COLS) return OOB;
  return FLOOR;
}

export function isWalkable(tileId) {
  return tileId !== OOB;
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
