// Phase 3.0 NES topdown: 個別 PNG (chars 40 + tiles 16) を PIXI.Assets で並列ロード。
// 戻り値:
//   loadCharSheet() → { souther: {down:[t,t], up:[t,t], left:[t,t], right:[t,t]}, yuko: {...}, ... }
//   loadTileset()   → { floor_carpet_a: Texture, wall_top: Texture, ..., counter_reception: Texture }
// 失敗時は null (scene.js は Graphics 矩形フォールバック / 床のみ縮退)。

const AGENTS = ["souther", "yuko", "writer", "designer", "engineer"];
const FACING_ABBR = { down: "dn", up: "up", left: "lf", right: "rt" };

const TILE_NAMES = [
  "floor_carpet_a", "floor_carpet_b", "wall_top", "wall_side",
  "throne_top", "throne_bottom",
  "desk_yuko", "desk_writer", "desk_designer", "desk_engineer",
  "counter_reception", "door", "plant", "document_pile", "rug_red",
];

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

export async function loadTileset(baseUrl = "/pixel-static/sprites/tiles") {
  try {
    const out = {};
    const tasks = TILE_NAMES.map(async (name) => {
      out[name] = await loadOne(`${baseUrl}/${name}.png`);
    });
    await Promise.all(tasks);
    return out;
  } catch (err) {
    console.warn("[pixel] tileset load failed:", err);
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

export { AGENTS, FACING_ABBR, TILE_NAMES };
