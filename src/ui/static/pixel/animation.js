// GSAP 連携。歩行 (walkTo) と訪問 (visitDesk) を提供。
// GSAP は ESM CDN から動的 import。

import gsap from "https://cdn.jsdelivr.net/npm/gsap@3.12.5/+esm";
import { CHAR_DEFS } from "/pixel-static/characters.js";

export { gsap };

/**
 * makeAnimator(charactersById)
 *   charactersById: { agent: PIXI.Container } — buildCharacter() の戻り値マップ
 *   戻り値: { walkTo, visitDesk, settleAt, stopAll, homePos }
 */
export function makeAnimator(charactersById) {
  const activeTimelines = new Map();
  const homePos = {};
  for (const [agent, c] of Object.entries(charactersById)) {
    homePos[agent] = { x: c.x, y: c.y };
  }

  function setPose(agent, pose) {
    const c = charactersById[agent];
    if (c && typeof c.setState === "function") c.setState(pose);
  }

  /** 単発: 指定座標へ移動 (歩行 → endPose) */
  function walkTo(agent, target, opts = {}) {
    const c = charactersById[agent];
    if (!c) return null;
    setPose(agent, "walking");
    return gsap.to(c, {
      x: target.x,
      y: target.y,
      duration: opts.duration ?? 0.85,
      ease: "power2.inOut",
      onComplete: () => setPose(agent, opts.endPose ?? "idle"),
    });
  }

  /**
   * 訪問: visitor が host の机近くへ歩く → dwellMs 滞在 → ホームへ戻る
   * dispatch / consult / evaluate で使う。
   */
  function visitDesk(visitor, host, dwellMs = 1200) {
    const c = charactersById[visitor];
    if (!c || !CHAR_DEFS[host]) return null;

    // 重複起動を防ぐ
    activeTimelines.get(visitor)?.kill();

    const home = homePos[visitor];
    const hostDef = CHAR_DEFS[host];
    const dest = { x: hostDef.x - 56, y: hostDef.y + 18 };

    const tl = gsap.timeline({
      onComplete: () => activeTimelines.delete(visitor),
    });

    tl.call(() => setPose(visitor, "walking"));
    tl.to(c, { x: dest.x, y: dest.y, duration: 0.9, ease: "power2.inOut" });
    tl.call(() => setPose(visitor, "talking"));
    tl.to({}, { duration: dwellMs / 1000 });
    tl.call(() => setPose(visitor, "walking"));
    tl.to(c, { x: home.x, y: home.y, duration: 0.9, ease: "power2.inOut" });
    tl.call(() => setPose(visitor, "idle"));

    activeTimelines.set(visitor, tl);
    return tl;
  }

  /** 任意の状態に切替 (歩かない、その場で state のみ) */
  function settleAt(agent, pose) {
    setPose(agent, pose);
  }

  /**
   * 一時ポーズ: 指定 pose に切替 → dwellMs 待つ → idle に戻る。
   * サザンの decree / 慟哭 / 高笑い 等の演出に使う。
   */
  function strikePose(agent, pose, dwellMs = 2000) {
    setPose(agent, pose);
    return gsap.to({}, {
      duration: dwellMs / 1000,
      onComplete: () => setPose(agent, "idle"),
    });
  }

  /** デバッグ用: 全停止して home へワープ */
  function stopAll() {
    for (const tl of activeTimelines.values()) tl.kill();
    activeTimelines.clear();
    for (const [agent, c] of Object.entries(charactersById)) {
      gsap.killTweensOf(c);
      c.x = homePos[agent].x;
      c.y = homePos[agent].y;
      setPose(agent, "idle");
    }
  }

  return { walkTo, visitDesk, settleAt, strikePose, stopAll, homePos };
}
