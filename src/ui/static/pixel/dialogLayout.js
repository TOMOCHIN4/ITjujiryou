// 会話パネル (壁面 2 枠) の left / right スロット解決。
// 規則:
//   1. デスク x が異なるペア → 小さい方=左、大きい方=右
//   2. 中央タイ (x=7.5 同士) → ユウコが含まれるなら必ず yuko=右
//   3. 中央タイで yuko 不在 (souther ⇔ designer) → 階級下=左、上=右

import { CHAR_DEFS } from "/pixel-static/characters.js";

const DESK_X = {
  souther:  7.5,
  yuko:     7.5,
  writer:   3,
  designer: 7.5,
  engineer: 12,
};

// 階級が小さいほど偉い。souther > yuko > brothers (writer/designer/engineer は同列)
const HIERARCHY_RANK = {
  souther:  0,
  yuko:     1,
  writer:   2,
  designer: 2,
  engineer: 2,
};

// 単独表示 (showSingle / addThought) のときの既定スロット。
// 概ねデスク x に沿って割る。yuko は規則 2 の延長で右固定。
const SOLO_SIDE = {
  souther:  "right",
  yuko:     "right",
  writer:   "left",
  designer: "left",
  engineer: "right",
};

/** PIXI 0xRRGGBB → CSS "#rrggbb" */
function toCssColor(num) {
  return "#" + num.toString(16).padStart(6, "0");
}

export const CHAR_CSS_COLOR = Object.fromEntries(
  Object.entries(CHAR_DEFS).map(([id, def]) => [id, toCssColor(def.color)])
);

/**
 * 2 キャラの会話における left / right スロットを返す。
 * @param {string} a エージェント ID
 * @param {string} b エージェント ID
 * @returns {{left: string, right: string} | null}
 */
export function resolveSlots(a, b) {
  if (!a || !b || a === b) return null;
  const xa = DESK_X[a];
  const xb = DESK_X[b];
  if (xa == null || xb == null) return null;

  if (xa < xb) return { left: a, right: b };
  if (xa > xb) return { left: b, right: a };

  // 中央タイ。規則 2: yuko は右固定
  if (a === "yuko") return { left: b, right: a };
  if (b === "yuko") return { left: a, right: b };

  // 規則 3: 階級下=左、上=右
  const ra = HIERARCHY_RANK[a] ?? 9;
  const rb = HIERARCHY_RANK[b] ?? 9;
  if (ra < rb) return { left: b, right: a };
  if (ra > rb) return { left: a, right: b };
  // 完全タイは入力順 (実用上あり得ない)
  return { left: a, right: b };
}

/** 単独表示時の既定 slot ("left" | "right")。 */
export function soloSide(agent) {
  return SOLO_SIDE[agent] || "right";
}

export function charName(agent) {
  return CHAR_DEFS[agent]?.name || agent;
}

export function charRole(agent) {
  return CHAR_DEFS[agent]?.role || "";
}
