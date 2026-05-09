// Phase 3.0 NES topdown: tile-step 移動とBFS経路。animation.js (GSAP timeline 集約) の後継。
//
// makeMovement(charactersById):
//   - walkPath(agent, [{tx,ty}, ...], opts): 各 tile を 0.18s linear で歩く
//   - visitDesk(visitor, host, dwellMs=1500): host 隣接タイルへ往復
//   - settleAt(agent, facing): その場で idle + 向き
//   - stopAll(): 全 timeline 停止 + home に戻す
//
// 戻り値の charTilePos は外部から読み取り可 (デバッグ用)

import gsap from "https://cdn.jsdelivr.net/npm/gsap@3.12.5/+esm";
import {
  TILE_SIZE, MAP_COLS, MAP_ROWS, tileAt, isWalkable,
  CHAR_HOME_TILE, tileToCharX, tileToCharY,
} from "/pixel-static/tilemap.js";

const STEP_MS = 180;  // 1 タイル 0.18 秒
const FACINGS = ["down", "up", "left", "right"];

function facingFromTo(a, b) {
  const dx = b.tx - a.tx, dy = b.ty - a.ty;
  if (dx > 0) return "right";
  if (dx < 0) return "left";
  if (dy > 0) return "down";
  return "up";
}

export function makeMovement(charactersById) {
  const activeTimelines = new Map();
  const charTilePos = {};
  for (const [agent, c] of Object.entries(charactersById)) {
    const home = CHAR_HOME_TILE[agent] || { tx: 0, ty: 0 };
    charTilePos[agent] = { ...home };
  }

  function setPose(agent, state, facing) {
    const c = charactersById[agent];
    if (c?.setState) c.setState(state, facing);
  }

  /** BFS で from → to の 4 方向経路を算出。終点は isWalkable 不問。
   *  occupied (Set<"tx,ty">) のタイルは avoid。到達不能なら []。 */
  function bfsPath(from, to, occupied = new Set()) {
    if (from.tx === to.tx && from.ty === to.ty) return [];
    const key = (t) => `${t.tx},${t.ty}`;
    const visited = new Set([key(from)]);
    const queue = [{ tx: from.tx, ty: from.ty, parent: null }];
    while (queue.length) {
      const cur = queue.shift();
      for (const [dx, dy] of [[0, 1], [0, -1], [1, 0], [-1, 0]]) {
        const nx = cur.tx + dx, ny = cur.ty + dy;
        const k = `${nx},${ny}`;
        if (visited.has(k)) continue;
        if (nx < 0 || nx >= MAP_COLS || ny < 0 || ny >= MAP_ROWS) continue;
        const isGoal = nx === to.tx && ny === to.ty;
        if (!isGoal) {
          if (!isWalkable(tileAt(nx, ny))) continue;
          if (occupied.has(k)) continue;
        }
        const node = { tx: nx, ty: ny, parent: cur };
        visited.add(k);
        if (isGoal) {
          const path = [];
          let n = node;
          while (n.parent) { path.unshift({ tx: n.tx, ty: n.ty }); n = n.parent; }
          return path;
        }
        queue.push(node);
      }
    }
    return [];
  }

  function currentOccupiedTiles(exclude) {
    const set = new Set();
    for (const [a, p] of Object.entries(charTilePos)) {
      if (a === exclude) continue;
      set.add(`${p.tx},${p.ty}`);
    }
    return set;
  }

  /** host home の上下左右で walkable な tile を 1 つ返す (順位 down→right→left→up) */
  function pickDestNearHost(host, occupied) {
    const home = CHAR_HOME_TILE[host];
    if (!home) return null;
    const cands = [
      { tx: home.tx, ty: home.ty + 1 },
      { tx: home.tx + 1, ty: home.ty },
      { tx: home.tx - 1, ty: home.ty },
      { tx: home.tx, ty: home.ty - 1 },
    ];
    for (const c of cands) {
      if (c.tx < 0 || c.tx >= MAP_COLS || c.ty < 0 || c.ty >= MAP_ROWS) continue;
      if (!isWalkable(tileAt(c.tx, c.ty))) continue;
      if (occupied.has(`${c.tx},${c.ty}`)) continue;
      return c;
    }
    return home;
  }

  /** 経路 (tile 配列) を 0.18s × N で滑らか歩行。各 tile 開始時に向きを更新 */
  function walkPath(agent, path, opts = {}) {
    const c = charactersById[agent];
    if (!c || path.length === 0) {
      opts.onComplete?.();
      return null;
    }
    activeTimelines.get(agent)?.kill();

    const tl = gsap.timeline({
      onComplete: () => {
        activeTimelines.delete(agent);
        setPose(agent, "idle", opts.endFacing ?? c._facing ?? "down");
        opts.onComplete?.();
      },
    });

    let prev = { ...charTilePos[agent] };
    for (const step of path) {
      const facing = facingFromTo(prev, step);
      tl.call(() => setPose(agent, "walking", facing));
      tl.to(c, {
        x: tileToCharX(step.tx),
        y: tileToCharY(step.ty),
        duration: STEP_MS / 1000,
        ease: "none",
        onUpdate: () => { c.zIndex = 20 + c.y; },
      });
      tl.call(() => { charTilePos[agent] = { tx: step.tx, ty: step.ty }; });
      prev = { tx: step.tx, ty: step.ty };
    }

    activeTimelines.set(agent, tl);
    return tl;
  }

  /** visitor が host の home 隣接へ往復 */
  function visitDesk(visitor, host, dwellMs = 1500) {
    const c = charactersById[visitor];
    if (!c) return null;
    const home = CHAR_HOME_TILE[visitor];
    const hostHome = CHAR_HOME_TILE[host];
    if (!home || !hostHome) return null;

    const occupiedOut = currentOccupiedTiles(visitor);
    const dest = pickDestNearHost(host, occupiedOut);
    if (!dest) return null;
    const dwellFacing = facingFromTo(dest, hostHome);

    const fromTile = { ...charTilePos[visitor] };
    const pathOut = bfsPath(fromTile, dest, occupiedOut);
    if (pathOut.length === 0 && (fromTile.tx !== dest.tx || fromTile.ty !== dest.ty)) {
      // 到達不能 — 吹き出しだけは出すので no-op
      return null;
    }

    activeTimelines.get(visitor)?.kill();
    const tl = gsap.timeline({ onComplete: () => activeTimelines.delete(visitor) });

    // 往路
    let prev = fromTile;
    for (const step of pathOut) {
      const facing = facingFromTo(prev, step);
      tl.call(() => setPose(visitor, "walking", facing));
      tl.to(c, {
        x: tileToCharX(step.tx), y: tileToCharY(step.ty),
        duration: STEP_MS / 1000, ease: "none",
        onUpdate: () => { c.zIndex = 20 + c.y; },
      });
      tl.call(() => { charTilePos[visitor] = { tx: step.tx, ty: step.ty }; });
      prev = { tx: step.tx, ty: step.ty };
    }

    // 滞在 (host の方向を向く)
    tl.call(() => setPose(visitor, "idle", dwellFacing));
    tl.to({}, { duration: dwellMs / 1000 });

    // 帰路 (BFS は dest → home、占有再計算)
    tl.call(() => {
      const occupiedReturn = currentOccupiedTiles(visitor);
      const pathBack = bfsPath(charTilePos[visitor], home, occupiedReturn);
      if (pathBack.length === 0) {
        setPose(visitor, "idle", "down");
        return;
      }
      // 帰路用のサブ timeline を即時実行
      const sub = gsap.timeline({
        onComplete: () => setPose(visitor, "idle", "down"),
      });
      let p = { ...charTilePos[visitor] };
      for (const step of pathBack) {
        const facing = facingFromTo(p, step);
        sub.call(() => setPose(visitor, "walking", facing));
        sub.to(c, {
          x: tileToCharX(step.tx), y: tileToCharY(step.ty),
          duration: STEP_MS / 1000, ease: "none",
          onUpdate: () => { c.zIndex = 20 + c.y; },
        });
        sub.call(() => { charTilePos[visitor] = { tx: step.tx, ty: step.ty }; });
        p = { tx: step.tx, ty: step.ty };
      }
      // 元の timeline は既に終了する。返す sub は activeTimelines を更新
      activeTimelines.set(visitor, sub);
    });

    activeTimelines.set(visitor, tl);
    return tl;
  }

  function settleAt(agent, facing = "down") {
    setPose(agent, "idle", facing);
  }

  function stopAll() {
    for (const tl of activeTimelines.values()) tl.kill();
    activeTimelines.clear();
    for (const [agent, c] of Object.entries(charactersById)) {
      gsap.killTweensOf(c);
      const home = CHAR_HOME_TILE[agent];
      c.x = tileToCharX(home.tx);
      c.y = tileToCharY(home.ty);
      c.zIndex = 20 + c.y;
      charTilePos[agent] = { ...home };
      setPose(agent, "idle", "down");
    }
  }

  return { walkPath, visitDesk, settleAt, stopAll, bfsPath, charTilePos };
}
