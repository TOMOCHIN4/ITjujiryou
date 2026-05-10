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
const BROTHERS = new Set(["writer", "designer", "engineer"]);

// 訪問者の最大滞在時間 (ms)。相手が応答しなかったときの最終帰宅トリガ。
// 通常は dialogPanel の onTtlExpire (返答パネル消滅) で先に解放されるため、
// ここに到達するのは「相手から返答が来ない」ケースだけ。
const SAFETY_DWELL_MS = 120000;

function facingFromTo(a, b) {
  const dx = b.tx - a.tx, dy = b.ty - a.ty;
  if (dx > 0) return "right";
  if (dx < 0) return "left";
  if (dy > 0) return "down";
  return "up";
}

/**
 * 物語的な動線を scripted で返す。BFS の最短経路ではなく、
 * 「真上に登る → 直角に曲がる → 横移動して停止」型の L 字経路。
 * 該当ペア以外は null を返し、呼び出し側は BFS にフォールバック。
 *
 * Returns: { pathOut: [...], dwellFacing, pathBack: [...] } または null
 */
function planScriptedPath(visitor, host) {
  // 三兄弟 → ユウコ
  if (host === "yuko" && BROTHERS.has(visitor)) {
    const visitorHome = CHAR_HOME_TILE[visitor];
    const homeTx = visitorHome.tx;
    const homeTy = visitorHome.ty;

    // Toshi (tx=7.5、center) は真上に 1 タイルだけ歩く。整数化すると 0.5 タイル右にズレるので
    // 浮動座標のまま animation する (walkPath は tileToCharX/Y で float OK)。
    if (homeTx >= 7 && homeTx <= 8) {
      return {
        pathOut: [{ tx: homeTx, ty: homeTy - 1 }],
        dwellFacing: "up",
        pathBack: [{ tx: homeTx, ty: homeTy }],
      };
    }

    // 端 (Haoh, Senshirou) は整数 L 字: 真上 → ユウコ高さ → 横に脇へ
    const startTx = Math.round(homeTx);
    const startTy = Math.round(homeTy);
    const meetTy = 6;
    let stopTx, dwellFacing;
    if (startTx < 7) {
      stopTx = 4;  // Yuko desk west edge の外側
      dwellFacing = "right";
    } else {
      stopTx = 11; // Yuko desk east edge の外側
      dwellFacing = "left";
    }

    const pathOut = [];
    // 1) 真上に登る
    for (let y = startTy - 1; y >= meetTy; y--) pathOut.push({ tx: startTx, ty: y });
    // 2) 横に曲がる
    if (stopTx > startTx) {
      for (let x = startTx + 1; x <= stopTx; x++) pathOut.push({ tx: x, ty: meetTy });
    } else if (stopTx < startTx) {
      for (let x = startTx - 1; x >= stopTx; x--) pathOut.push({ tx: x, ty: meetTy });
    }

    // 帰路は逆順 (横戻し → 下に降りる)
    // ※ 最後の y は startTy-1 まで (= home 行の 1 つ上)。最終 0.5 タイルは snapBackToFloatHome に任せて z-glitch 回避。
    const pathBack = [];
    if (stopTx > startTx) {
      for (let x = stopTx - 1; x >= startTx; x--) pathBack.push({ tx: x, ty: meetTy });
    } else if (stopTx < startTx) {
      for (let x = stopTx + 1; x <= startTx; x++) pathBack.push({ tx: x, ty: meetTy });
    }
    for (let y = meetTy + 1; y < startTy; y++) pathBack.push({ tx: startTx, ty: y });

    return { pathOut, dwellFacing, pathBack };
  }

  // ユウコ → サザン: 真上に 1 タイルだけ歩く (浮動座標を維持して右にズレないように)
  if (visitor === "yuko" && host === "souther") {
    const yukoHome = CHAR_HOME_TILE.yuko;
    return {
      pathOut: [{ tx: yukoHome.tx, ty: yukoHome.ty - 1 }],
      dwellFacing: "up",
      pathBack: [{ tx: yukoHome.tx, ty: yukoHome.ty }],
    };
  }

  return null;
}

export function makeMovement(charactersById) {
  const activeTimelines = new Map();
  // dwellState: visitor が host 席に着いてパネル消失を待っている状態
  //   visitor → { host, startReturn, safetyTimer }
  const dwellState = new Map();
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
   *  occupied (Set<"tx,ty">) のタイルは avoid。到達不能なら []。
   *  CHAR_HOME_TILE は小数を含む (例: 2.8) ので整数 tile グリッドで動作させる。 */
  function bfsPath(from, to, occupied = new Set()) {
    const fromR = { tx: Math.round(from.tx), ty: Math.round(from.ty) };
    const toR = { tx: Math.round(to.tx), ty: Math.round(to.ty) };
    if (fromR.tx === toR.tx && fromR.ty === toR.ty) return [];
    from = fromR;
    to = toR;
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

  /**
   * visitor が host の home 隣接へ往復。
   * 滞在は固定タイマではなく **外部 release 待ち** (dialogPanel の onTtlExpire 経由)。
   * 安全弁として SAFETY_DWELL_MS で自動帰宅。
   * 第 3 引数 dwellMs は無視 (互換のため残す)。
   */
  function visitDesk(visitor, host, _dwellMsIgnored = 0) {
    const c = charactersById[visitor];
    if (!c) return null;
    const home = CHAR_HOME_TILE[visitor];
    const hostHome = CHAR_HOME_TILE[host];
    if (!home || !hostHome) return null;

    // scripted な動線が定義されている (visitor, host) ペアはそれを優先
    const scripted = planScriptedPath(visitor, host);

    let pathOut, dwellFacing, scriptedBack = null;
    if (scripted) {
      pathOut = scripted.pathOut;
      dwellFacing = scripted.dwellFacing;
      scriptedBack = scripted.pathBack;
    } else {
      const occupiedOut = currentOccupiedTiles(visitor);
      const dest = pickDestNearHost(host, occupiedOut);
      if (!dest) return null;
      dwellFacing = facingFromTo(dest, hostHome);
      const fromTile0 = { ...charTilePos[visitor] };
      pathOut = bfsPath(fromTile0, dest, occupiedOut);
      if (pathOut.length === 0 && (fromTile0.tx !== dest.tx || fromTile0.ty !== dest.ty)) {
        return null;
      }
    }
    const fromTile = { ...charTilePos[visitor] };

    // 既存の dwell があればクリア (再呼び出しで上書き)
    const prevDwell = dwellState.get(visitor);
    if (prevDwell) {
      clearTimeout(prevDwell.safetyTimer);
      dwellState.delete(visitor);
    }
    activeTimelines.get(visitor)?.kill();

    // home が小数の場合 (yuko 5.5、souther 2.8) は最後に float home へ snap。
    const snapBackToFloatHome = () => {
      c.x = tileToCharX(home.tx);
      c.y = tileToCharY(home.ty);
      c.zIndex = 20 + c.y;
      charTilePos[visitor] = { tx: home.tx, ty: home.ty };
      setPose(visitor, "idle", "down");
      activeTimelines.delete(visitor);
    };

    // 帰路実行: dwellState からエントリを消し、帰路 timeline を即時走らせる。
    const startReturn = () => {
      const entry = dwellState.get(visitor);
      if (!entry) return;
      clearTimeout(entry.safetyTimer);
      dwellState.delete(visitor);

      let pathBack;
      if (scriptedBack) {
        pathBack = scriptedBack;
      } else {
        const occupiedReturn = currentOccupiedTiles(visitor);
        pathBack = bfsPath(charTilePos[visitor], home, occupiedReturn);
      }
      if (pathBack.length === 0) {
        snapBackToFloatHome();
        return;
      }
      const sub = gsap.timeline({ onComplete: snapBackToFloatHome });
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
      activeTimelines.set(visitor, sub);
    };

    // 往路 timeline: 完了したら dwellState に登録 + 安全弁発動 (release 待ち)
    const tlOut = gsap.timeline({
      onComplete: () => {
        setPose(visitor, "idle", dwellFacing);
        const safetyTimer = setTimeout(startReturn, SAFETY_DWELL_MS);
        dwellState.set(visitor, { host, startReturn, safetyTimer });
        // 往路 timeline 自体はここで終わる
      },
    });

    let prev = fromTile;
    for (const step of pathOut) {
      const facing = facingFromTo(prev, step);
      tlOut.call(() => setPose(visitor, "walking", facing));
      tlOut.to(c, {
        x: tileToCharX(step.tx), y: tileToCharY(step.ty),
        duration: STEP_MS / 1000, ease: "none",
        onUpdate: () => { c.zIndex = 20 + c.y; },
      });
      tlOut.call(() => { charTilePos[visitor] = { tx: step.tx, ty: step.ty }; });
      prev = { tx: step.tx, ty: step.ty };
    }

    activeTimelines.set(visitor, tlOut);
    return tlOut;
  }

  /** 外部から release: dwell 中なら帰路を即時開始。それ以外は no-op。 */
  function releaseVisitor(visitor) {
    const entry = dwellState.get(visitor);
    if (!entry) return false;
    entry.startReturn();
    return true;
  }

  function isDwelling(visitor) {
    return dwellState.has(visitor);
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

  return { walkPath, visitDesk, settleAt, stopAll, bfsPath, charTilePos, releaseVisitor, isDwelling };
}
