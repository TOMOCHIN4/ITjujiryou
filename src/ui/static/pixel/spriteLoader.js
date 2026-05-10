// Phase 3.0 NES topdown: 個別 PNG (chars 40 + 背景/装飾/デスク) を PIXI.Assets で並列ロード。
// 戻り値:
//   loadCharSheet() → { souther: {down:[t,t], up:[t,t], left:[t,t], right:[t,t]}, yuko: {...}, ... }
// 失敗時は null (scene.js は Graphics 矩形フォールバック / 床のみ縮退)。

const AGENTS = ["souther", "yuko", "writer", "designer", "engineer"];
const FACING_ABBR = { down: "dn", up: "up", left: "lf", right: "rt" };

async function loadOne(url) {
  return await PIXI.Assets.load(url);
}

export async function loadCharSheet(baseUrl = "/pixel-static/sprites/chars") {
  try {
    const out = {};
    const tasks = [];
    for (const agent of AGENTS) {
      out[agent] = {};
      for (const [facing, abbr] of Object.entries(FACING_ABBR)) {
        tasks.push(
          (async () => {
            const a = await loadOne(`${baseUrl}/${agent}_${abbr}_a.png`);
            const b = await loadOne(`${baseUrl}/${agent}_${abbr}_b.png`);
            out[agent][facing] = [a, b];
          })()
        );
      }
    }
    await Promise.all(tasks);
    return out;
  } catch (err) {
    console.warn("[pixel] char sheet load failed:", err);
    return null;
  }
}

export async function loadBackground(url = "/pixel-static/sprites/background/office.png") {
  try {
    return await loadOne(url);
  } catch (err) {
    console.warn("[pixel] background load failed:", err);
    return null;
  }
}

export async function loadDecor(baseUrl = "/pixel-static/sprites/decor") {
  try {
    return {
      motto_plaque: await loadOne(`${baseUrl}/motto_plaque.png`),
    };
  } catch (err) {
    console.warn("[pixel] decor load failed:", err);
    return null;
  }
}

export async function loadDesks(baseUrl = "/pixel-static/sprites/furniture") {
  try {
    const out = {};
    const tasks = AGENTS.map(async (agent) => {
      out[agent] = await loadOne(`${baseUrl}/desk_${agent}.png`);
    });
    await Promise.all(tasks);
    return out;
  } catch (err) {
    console.warn("[pixel] desks load failed:", err);
    return null;
  }
}
