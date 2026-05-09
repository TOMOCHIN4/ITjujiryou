// Phase 2: 4 キャラ (yuko/writer/designer/engineer) × 4 ポーズの個別 PNG を PIXI.Assets で並列ロード。
// Phase 2.5: サザンは別ローダー (loadSazanTextures) で 36 ポーズの豊富なセットをロード。
//
// 戻り値: { agent: { pose: Texture[] } }  ※AnimatedSprite 互換のため Texture 配列
// 失敗時は当該キャラを欠落で返す (フロント側がフォールバック処理)。

const STAFF_AGENTS = ["yuko", "writer", "designer", "engineer"];
const STAFF_POSES = ["idle", "typing", "talking", "walking"];

// サザンの 36 ポーズ: 多フレーム (idle 8, walking 8, talking 4) + 静止 16
const SAZAN_IDLE = ["idle_1", "idle_2", "idle_3", "idle_4", "idle_5", "idle_6", "idle_7", "idle_8"];
const SAZAN_WALK = ["walk_1", "walk_2", "walk_3", "walk_4", "walk_5", "walk_6", "walk_7", "walk_8"];
const SAZAN_TALK = ["talk_1", "talk_2", "talk_3", "talk_4"];
const SAZAN_STATIC = [
  "proclaim_arms_wide", "point_decree_right", "fist_raised", "hand_stop",
  "nod_approve", "thinking_hand_chin", "looking_far_away", "tears_kneeling",
  "crying_arm_reach", "fuhahaha_laughing", "accept_defeat", "anger_burst",
  "throne_seated", "throne_proclaim", "back_view_standing", "close_emotion_softness",
];
const SAZAN_ALL = [...SAZAN_IDLE, ...SAZAN_WALK, ...SAZAN_TALK, ...SAZAN_STATIC];

async function loadOne(url) {
  return await PIXI.Assets.load(url);
}

export async function loadStaffTextures(baseUrl = "/pixel-static/sprites/staff") {
  const out = {};
  try {
    const tasks = STAFF_AGENTS.flatMap((agent) =>
      STAFF_POSES.map(async (pose) => {
        const tex = await loadOne(`${baseUrl}/${agent}_${pose}.png`);
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

/**
 * サザン 36 ポーズをロード。
 *
 * 戻り値: {
 *   idle: [tex × 8], walking: [tex × 8], talking: [tex × 4],
 *   proclaim_arms_wide: [tex], point_decree_right: [tex], ...
 * }
 *
 * ポーズ名は Character.setState(pose) でそのまま使える。multi-frame のものは AnimatedSprite で
 * 全フレームを順次再生、static のものは 1 フレーム表示。
 */
export async function loadSazanTextures(baseUrl = "/pixel-static/sprites/sazan") {
  try {
    const map = {};
    const tasks = SAZAN_ALL.map(async (name) => {
      map[name] = await loadOne(`${baseUrl}/${name}.png`);
    });
    await Promise.all(tasks);

    // multi-frame アニメ用にグルーピング
    const out = {
      idle: SAZAN_IDLE.map((n) => map[n]),
      walking: SAZAN_WALK.map((n) => map[n]),
      talking: SAZAN_TALK.map((n) => map[n]),
    };
    // 静止画はそれぞれ 1 要素配列で展開 (setState で同じ API)
    for (const name of SAZAN_STATIC) {
      out[name] = [map[name]];
    }
    return out;
  } catch (err) {
    console.warn("[pixel] sazan sprite load failed, falling back:", err);
    return null;
  }
}

export { STAFF_AGENTS, STAFF_POSES, SAZAN_IDLE, SAZAN_WALK, SAZAN_TALK, SAZAN_STATIC };
