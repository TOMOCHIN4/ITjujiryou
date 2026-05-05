"""クライアント窓口。発注 → ユウコ起動 → 応答返却。

ペルソナ漏れを最後の砦として後段でチェック。
"""
from __future__ import annotations

from src.events.logger import log
from src.memory.store import get_store
from src.orchestrator import run_yuko

FORBIDDEN_TERMS = [
    "帝王", "聖帝", "サウザー", "南斗", "鳳凰拳", "オウガイ", "お師さん",
    "ふん、", "下郎", "雑兵", "退かぬ", "媚びぬ", "省みぬ",
    # 平仮名表記の聖帝信条（漢字版だけだと素通りするケースがあるため）
    "ひかぬ", "こびぬ", "かえりみぬ",
    "愛などいらぬ", "ケンシロウ", "北斗",
]

# 内部独白判定用のキーワード（応答先頭にこれが含まれ、かつ "---" 区切りがあれば
# 先頭ブロックは社内向けの判断メモとみなして剥がす）
_INTERNAL_KEYWORDS = [
    "上申", "ご裁断", "裁断", "dispatch", "deliver", "承認", "評価", "判断",
    "本段階では", "再回答を待つ", "社内ツール", "最終応答テキスト",
    "品質は要件", "納品へ進む", "部下", "発注確定前",
]


def find_forbidden_terms(text: str) -> list[str]:
    return [t for t in FORBIDDEN_TERMS if t in text]


def _strip_internal_preamble(text: str) -> str:
    """ユウコ応答先頭の内部独白を剥がす。

    `---` のみからなる行が先頭付近にあり、その上のブロックが内部判断っぽい
    キーワードを含む場合のみ、その区切り以降を採用する。
    クライアント宛の通常文面（先頭から `お客様` で始まる等）は無傷で返す。
    """
    lines = text.splitlines()
    # 先頭から最初の "---" 単独行を探す（先頭 30 行以内に限定）
    sep_idx = -1
    for i, line in enumerate(lines[:30]):
        if line.strip() == "---":
            sep_idx = i
            break
    if sep_idx <= 0:
        return text
    preamble = "\n".join(lines[:sep_idx])
    if not any(kw in preamble for kw in _INTERNAL_KEYWORDS):
        return text  # 内部独白っぽくない `---` は触らない
    body = "\n".join(lines[sep_idx + 1:]).lstrip("\n")
    return body or text


async def handle_client_message(text: str, task_id: str | None = None) -> str:
    """クライアントから受信し、ユウコの応答を返す。

    新規発注なら task を作成、既存案件への追加メッセージなら task_id を渡す。
    """
    store = get_store()

    if task_id is None:
        task_id = await store.create_task(
            title=text[:60],
            description=text,
            client_request=text,
        )

    await store.add_message("client", "yuko", text, "email", task_id)
    await log("client", f"→ yuko: {text[:200]}", event_type="message", task_id=task_id)

    yuko_input = (
        f"クライアントから以下の連絡が届きました。\n"
        f"案件ID: {task_id}\n\n"
        f"--- 受信内容 ---\n{text}\n----------------\n\n"
        "営業主任として対応してください。新規発注なら社長への上申を経て"
        "適切な部下に dispatch_task で振り、最終的に deliver で納品まで完遂すること。"
        "クライアントへの最終応答テキストを、あなたの応答本文として返してください。"
    )

    response = await run_yuko(yuko_input, task_id=task_id)
    response = _strip_internal_preamble(response)

    leaks = find_forbidden_terms(response)
    if leaks:
        await log(
            "system",
            f"⚠ ペルソナ漏れ検知: {leaks} → 再生成を依頼",
            event_type="persona_leak",
            task_id=task_id,
        )
        retry_input = (
            "あなたの直前の応答にクライアント禁止用語が含まれていました: "
            f"{leaks}。\n禁止用語を完全に取り除いた、クライアント向けの正式な"
            "応答文だけを返してください。社内用語・社長の聖帝口調は一切引用しないこと。"
        )
        response = await run_yuko(retry_input, task_id=task_id)
        response = _strip_internal_preamble(response)
        leaks2 = find_forbidden_terms(response)
        if leaks2:
            # 二度目も漏れたら強制マスク
            for term in leaks2:
                response = response.replace(term, "■")
            await log(
                "system",
                f"⚠ 再生成後も漏れ: {leaks2} → マスク済み",
                event_type="persona_leak",
                task_id=task_id,
            )

    await store.add_message("yuko", "client", response, "email", task_id)
    await log("yuko", f"→ client: {response[:200]}", event_type="message", task_id=task_id)
    return response
