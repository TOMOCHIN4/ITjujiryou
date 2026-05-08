// Phase 2: 5キャラ × 4ポーズの個別 PNG を PIXI.Assets で並列ロード。
// 戻り値: { agent: { pose: Texture[] } }  ※AnimatedSprite 互換のため Texture 配列で返す
// 失敗時は null を返してフォールバック (Phase 1 の Graphics 矩形描画) を発動。

const AGENTS = ["souther", "yuko", "writer", "designer", "engineer"];
const POSES = ["idle", "typing", "talking", "walking"];

export async function loadStaffTextures(baseUrl = "/pixel-static/sprites/staff") {
  const out = {};
  try {
    const tasks = AGENTS.flatMap((agent) =>
      POSES.map(async (pose) => {
        const url = `${baseUrl}/${agent}_${pose}.png`;
        const tex = await PIXI.Assets.load(url);
        out[agent] ??= {};
        out[agent][pose] = [tex];
      })
    );
    await Promise.all(tasks);
    return out;
  } catch (err) {
    console.warn("[pixel] staff sprite load failed, falling back:", err);
    return null;
  }
}

export { AGENTS, POSES };
