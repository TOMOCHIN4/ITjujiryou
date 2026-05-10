// 物理移動許可とクライアント判定の単一の真実。
// 物語ルール:
//   - サザンは微動だにしない (常に玉座)
//   - ユウコはサザンとの間のみ往復、ブラザー (writer/designer/engineer) のところへは行かない
//   - ブラザーは自席 ↔ ユウコ席のみ
//   - 上記以外の対話は声/メールのみ (移動なし)

const BROTHERS = new Set(["writer", "designer", "engineer"]);

/**
 * visitor が host のところまで物理的に歩いて行ってよいか。
 * @param {string} visitor 動こうとしているキャラ
 * @param {string} host 訪問先のキャラ
 * @returns {boolean}
 */
export function canPhysicallyMove(visitor, host) {
  if (!visitor || !host || visitor === host) return false;
  // サザンは絶対に動かない、誰もサザンのところへ行かない (ユウコ除く)
  if (visitor === "souther" || host === "souther") {
    return visitor === "yuko" && host === "souther";
  }
  // ユウコはブラザーのところへ自分から行かない
  if (visitor === "yuko") return false;
  // ブラザーはユウコ席までだけ
  if (BROTHERS.has(visitor)) return host === "yuko";
  return false;
}

/**
 * イベントがクライアント (外部) ↔ ユウコ のメールやり取りか。
 * メール条件:
 *   - 当事者にユウコが含まれる
 *   - かつ from_agent / to_agent が "client" を含む、または message_type === "email"
 */
export function isClientInteraction(ev) {
  if (!ev) return false;
  const d = ev.details || {};
  const involvesYuko = ev.agent === "yuko" || d.to_agent === "yuko" || d.from_agent === "yuko";
  const touchesClient = d.from_agent === "client" || d.to_agent === "client";
  const isEmail = d.message_type === "email";
  return involvesYuko && (touchesClient || isEmail);
}
