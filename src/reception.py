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
    "愛などいらぬ", "ケンシロウ", "北斗",
]


def find_forbidden_terms(text: str) -> list[str]:
    return [t for t in FORBIDDEN_TERMS if t in text]


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
