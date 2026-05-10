"""愛帝十字陵 stdio MCP サーバ。

各 Claude Code プロセス (workspaces/{role}/) が `.mcp.json` 経由でこのサーバを参照する。
registry.py のロジックをマルチプロセス前提に書き換えたもの。

主な変更点:
- run_agent / push_call / _call_chain は廃止 (プロセス分離されたため意味を持たない)
- send_message / dispatch_task は DB 投入のみで即 return (同期起動はしない)
- consult_peer / consult_souther は MCP tool 内で polling して疑似同期
- 起動チェーンの起こし役は外部の inbox_watcher が担う
"""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any, Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from src.events.logger import log
from src.memory.store import get_store

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUTS_DIR = REPO_ROOT / "outputs"

VALID_AGENTS = ("souther", "yuko", "designer", "engineer", "writer")
SUBORDINATES = ("designer", "engineer", "writer")

# 暴走防止パラメータ
MAX_AGENT_CALLS = int(os.environ.get("ITJUJIRYOU_MAX_AGENT_CALLS", "30"))
MAX_CONSULT_PAIR = 2
MAX_REVISION_ROUNDS = int(os.environ.get("ITJUJIRYOU_MAX_REVISION_ROUNDS", "2"))

# polling 設定
CONSULT_TIMEOUT_S = float(os.environ.get("ITJUJIRYOU_CONSULT_TIMEOUT_S", "60"))
POLL_INTERVAL_S = 0.5

server: Server = Server("itjujiryou")


def _text(s: str) -> list[TextContent]:
    return [TextContent(type="text", text=s)]


# ---------------------------------------------------------------------------
# Tool スキーマ定義
# ---------------------------------------------------------------------------


def _tool_defs() -> list[Tool]:
    return [
        Tool(
            name="send_message",
            description=(
                "社内メンバー (souther/yuko/designer/engineer/writer) にメッセージを送る。"
                "DB に書き込んで即 return する非同期送信。"
                "応答が必要な場合は consult_souther / consult_peer を使う。"
                "クライアント宛 (to=client) は禁止 — deliver を使うこと。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "from_agent": {"type": "string", "description": "送信者 (souther/yuko/...)"},
                    "to": {"type": "string", "description": "宛先"},
                    "content": {"type": "string"},
                    "task_id": {"type": "string", "description": "案件 ID (任意)"},
                    "message_type": {
                        "type": "string",
                        "description": "report / question / approval_request / directive / notice",
                    },
                },
                "required": ["from_agent", "to", "content"],
            },
        ),
        Tool(
            name="dispatch_task",
            description=(
                "ユウコ専用。部下 (designer/engineer/writer) に構造化チケットでタスクを発注する。"
                "DB に subtask + dispatch メッセージを書いて即 return する。"
                "部下プロセスは inbox_watcher 経由で起動される。"
                "完了報告は後で read_status で確認すること。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "from_agent": {"type": "string"},
                    "assigned_to": {"type": "string"},
                    "task_id": {"type": "string"},
                    "ticket_json": {"type": "string"},
                    "preceding_outputs_json": {"type": "string"},
                    "revision_round": {"type": "integer"},
                    "subtask_id": {"type": "string"},
                },
                "required": ["from_agent", "assigned_to", "task_id", "ticket_json"],
            },
        ),
        Tool(
            name="consult_peer",
            description=(
                "部下 (designer/engineer/writer) のみ使用可。隣の部下に専門相談を投げ、"
                "同期的に応答を待つ (最大 60 秒の polling)。雑談禁止、技術判断のみ。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "from_agent": {"type": "string"},
                    "to": {"type": "string"},
                    "task_id": {"type": "string"},
                    "question": {"type": "string"},
                    "context": {"type": "string"},
                },
                "required": ["from_agent", "to", "task_id", "question"],
            },
        ),
        Tool(
            name="consult_souther",
            description=(
                "ユウコ専用。社長サウザーへ同期問い合わせ (最大 60 秒の polling)。"
                "新規案件の承認・値引き判断・品質基準の裁定など、社長の決裁が要る場面で使う。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "from_agent": {"type": "string"},
                    "task_id": {"type": "string"},
                    "content": {"type": "string"},
                    "message_type": {
                        "type": "string",
                        "description": "approval_request / question / directive (既定 approval_request)",
                    },
                },
                "required": ["from_agent", "task_id", "content"],
            },
        ),
        Tool(
            name="propose_plan",
            description=(
                "ユウコ専用。案件の初期計画を保存する。複合案件・規模中以上で必須。"
                "plan_json は {steps:[...], risks, milestones} 等。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string"},
                    "plan_json": {"type": "string"},
                },
                "required": ["task_id", "plan_json"],
            },
        ),
        Tool(
            name="evaluate_deliverable",
            description=(
                "ユウコ専用。部下成果物の品質判定。decision は approve/revise/escalate_to_president。"
                "revise を返した場合、必ず再 dispatch_task で revision_round を +1 して同一 subtask_id を渡す。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string"},
                    "subtask_id": {"type": "string"},
                    "evaluation": {"type": "string"},
                    "decision": {"type": "string"},
                    "round": {"type": "integer"},
                },
                "required": ["task_id", "subtask_id", "evaluation", "decision"],
            },
        ),
        Tool(
            name="update_status",
            description=(
                "案件の状態を更新する (received / hearing / approved / in_progress / "
                "review / delivered / cancelled)。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string"},
                    "new_status": {"type": "string"},
                    "notes": {"type": "string"},
                },
                "required": ["task_id", "new_status"],
            },
        ),
        Tool(
            name="read_status",
            description="案件の状態と関連情報を閲覧する。task_id を指定しなければ全件サマリ。",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string"},
                },
            },
        ),
        Tool(
            name="deliver",
            description=(
                "ユウコ専用。クライアントへの納品を行う。納品メール本文と成果物パスを記録。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string"},
                    "deliverable_paths_json": {"type": "string"},
                    "delivery_message": {"type": "string"},
                },
                "required": ["task_id", "deliverable_paths_json", "delivery_message"],
            },
        ),
        Tool(
            name="record_thought",
            description=(
                "ユウコ専用。クライアント案件を処理中の内省・心のうちを 1 文記録する。"
                "これは pixel UI のユウコパネル『心のうち』枠に表示される独白で、"
                "クライアント・社長・部下には届かない、純粋な表示用のフレーバー。"
                "業務判断や指示は含めず、感じたこと・気づき・小さな葛藤を 1 文で。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "from_agent": {"type": "string", "description": "発信者 (yuko 固定)"},
                    "text": {"type": "string", "description": "心のうち本文 (1〜2 文程度)"},
                    "task_id": {"type": "string", "description": "案件 ID (任意)"},
                },
                "required": ["from_agent", "text"],
            },
        ),
    ]


@server.list_tools()
async def list_tools() -> list[Tool]:
    return _tool_defs()


# ---------------------------------------------------------------------------
# Tool ハンドラ
# ---------------------------------------------------------------------------


async def _handle_send_message(args: dict[str, Any]) -> list[TextContent]:
    from_agent = args["from_agent"]
    to = args["to"]
    content = args["content"]
    task_id = args.get("task_id") or None
    message_type = args.get("message_type") or "report"

    if to not in VALID_AGENTS:
        return _text(f"ERROR: 不正な宛先 '{to}'。有効値: {VALID_AGENTS} (client は deliver を使うこと)")

    store = get_store()
    msg_id = await store.add_message(from_agent, to, content, message_type, task_id)
    await log(
        from_agent,
        f"→ {to} ({message_type}): {content[:120]}{'…' if len(content) > 120 else ''}",
        event_type="message",
        task_id=task_id,
        details={
            "from_agent": from_agent,
            "to_agent": to,
            "message_type": message_type,
            "preview": content[:200],
        },
    )
    return _text(
        f"OK: {to} 宛のメッセージを保存しました (msg_id={msg_id[:8]})。"
        "応答が必要な場合は consult_souther/consult_peer を使うか、"
        "後ほど read_status で確認してください。"
    )


async def _handle_dispatch_task(args: dict[str, Any]) -> list[TextContent]:
    from_agent = args["from_agent"]
    assigned_to = args["assigned_to"]
    task_id = args["task_id"]
    ticket_json = args["ticket_json"]
    preceding_outputs_json = args.get("preceding_outputs_json") or "[]"
    revision_round = int(args.get("revision_round") or 0)
    explicit_subtask_id = args.get("subtask_id") or None

    if from_agent != "yuko":
        return _text(f"ERROR: dispatch_task はユウコ専用。'{from_agent}' は使用不可。")
    if assigned_to not in SUBORDINATES:
        return _text(f"ERROR: 部下は {SUBORDINATES} のいずれか。'{assigned_to}' は不可。")

    try:
        ticket = json.loads(ticket_json)
    except json.JSONDecodeError as e:
        return _text(f"ERROR: ticket_json が不正な JSON: {e}")
    try:
        preceding = json.loads(preceding_outputs_json)
        if not isinstance(preceding, list):
            preceding = []
    except json.JSONDecodeError:
        preceding = []

    store = get_store()

    if await store.count_agent_calls(task_id) >= MAX_AGENT_CALLS:
        return _text(
            "ERROR: この案件のエージェント起動回数が上限に達しました。"
            "ユウコは自身で着地点を判断するか、社長へ escalate してください。"
        )

    if explicit_subtask_id and revision_round > MAX_REVISION_ROUNDS:
        return _text(
            f"ERROR: 修正回数が上限 ({MAX_REVISION_ROUNDS}) を超過。"
            "これ以上の revise は禁止。社長へ escalate_to_president を上申してください。"
        )

    sub_id = await store.create_subtask(
        task_id,
        assigned_to,
        ticket.get("objective", "")[:500],
        sub_id=explicit_subtask_id,
    )

    out_dir = OUTPUTS_DIR / task_id
    out_dir.mkdir(parents=True, exist_ok=True)

    preceding_block = ""
    if preceding:
        preceding_block = "\n--- 前工程の成果物 (preceding_outputs) ---\n"
        for item in preceding:
            preceding_block += (
                f"- from: {item.get('from','?')}\n"
                f"  paths: {item.get('paths', [])}\n"
                f"  summary: {item.get('summary','')}\n"
            )
        preceding_block += "----------------------------------------\n"

    round_note = ""
    if revision_round > 0:
        round_note = (
            f"\n【修正サイクル {revision_round} 回目】\n"
            "前回成果物に対するユウコの評価を踏まえ、ticket の objective に書かれた\n"
            "修正指示に従って改訂してください。\n"
        )

    dispatch_payload = (
        "営業主任ユウコより、以下の構造化チケットを受領しました。\n\n"
        f"案件ID: {task_id}\n"
        f"サブタスクID: {sub_id}\n"
        f"成果物保存先: outputs/{task_id}/\n"
        f"{round_note}"
        f"{preceding_block}\n"
        "--- チケット (JSON) ---\n"
        f"{json.dumps(ticket, ensure_ascii=False, indent=2)}\n"
        "----------------------\n\n"
        f"memory ディレクトリ (data/memory/{assigned_to}/) を確認し、"
        f"成果物を outputs/{task_id}/ に保存してください。"
        "完了したら send_message で yuko に report を送ってください。"
    )

    await store.add_message("yuko", assigned_to, dispatch_payload, "dispatch", task_id)
    await log(
        "yuko",
        f"dispatch_task → {assigned_to} (sub={sub_id[:8]}, round={revision_round})",
        event_type="dispatch",
        task_id=task_id,
        details={
            "assigned_to": assigned_to,
            "subtask_id": sub_id,
            "round": revision_round,
            "from_agent": "yuko",
            "to_agent": assigned_to,
            "message_type": "directive",
            "subject": f"📨 指示 (round {revision_round})",
        },
    )
    return _text(
        f"OK: {assigned_to} へ dispatch しました。\n"
        f"subtask_id: {sub_id}\n"
        f"revision_round: {revision_round}\n"
        f"成果物は outputs/{task_id}/ に出ます。完了報告は read_status か "
        "messages の {assigned_to}→yuko で確認してください。"
    )


async def _handle_consult_peer(args: dict[str, Any]) -> list[TextContent]:
    from_agent = args["from_agent"]
    to = args["to"]
    task_id = args["task_id"]
    question = args["question"]
    context = args.get("context") or ""

    if from_agent not in SUBORDINATES:
        return _text(f"ERROR: consult_peer は部下専用。'{from_agent}' は使用不可。")
    if to not in SUBORDINATES:
        return _text(f"ERROR: 相談相手は部下のみ。'{to}' は不可。")
    if to == from_agent:
        return _text("ERROR: 自分自身に相談はできません。")

    store = get_store()

    pair_count = await store.count_consult_pair(task_id, from_agent, to)
    if pair_count >= MAX_CONSULT_PAIR:
        return _text(
            f"ERROR: {from_agent}→{to} の相談回数が上限 ({MAX_CONSULT_PAIR}) を超過。"
        )
    if await store.count_agent_calls(task_id) >= MAX_AGENT_CALLS:
        return _text("ERROR: この案件のエージェント起動回数が上限に達しました。")

    payload = (
        f"【相談】{from_agent}より、技術的な相談が届きました。\n"
        f"案件ID: {task_id}\n\n"
        f"--- 相談内容 ---\n{question}\n----------------\n"
        + (f"\n--- 背景・補足 ---\n{context}\n----------------\n" if context else "")
        + "\nあなたの専門知識から簡潔に応答してください。"
        "send_message で from_agent={to} → to={from_agent}, message_type=consult_reply で返信してください。"
    )

    msg_id = await store.add_message(from_agent, to, payload, "consult", task_id)
    await log(
        from_agent,
        f"→ {to} (consult): {question[:120]}{'…' if len(question) > 120 else ''}",
        event_type="consult",
        task_id=task_id,
        details={
            "to": to,
            "from_agent": from_agent,
            "to_agent": to,
            "message_type": "consult",
            "preview": question[:200],
        },
    )

    reply = await _poll_reply(
        task_id=task_id,
        from_agent=to,
        to_agent=from_agent,
        after_id=msg_id,
        message_type="consult_reply",
    )
    if reply is None:
        return _text(
            f"ERROR: {to} から {CONSULT_TIMEOUT_S:.0f} 秒以内に応答がありませんでした。"
            "後で read_status で確認するか、別アプローチを取ってください。"
        )
    return _text(f"{to} からの応答:\n\n{reply}")


async def _handle_consult_souther(args: dict[str, Any]) -> list[TextContent]:
    from_agent = args["from_agent"]
    task_id = args["task_id"]
    content = args["content"]
    message_type = args.get("message_type") or "approval_request"

    if from_agent != "yuko":
        return _text(f"ERROR: consult_souther はユウコ専用。'{from_agent}' は使用不可。")

    store = get_store()
    if await store.count_agent_calls(task_id) >= MAX_AGENT_CALLS:
        return _text(
            "ERROR: この案件のエージェント起動回数が上限に達しました。"
            "ユウコは自身で判断するか、案件を分割してください。"
        )

    msg_id = await store.add_message(from_agent, "souther", content, message_type, task_id)
    await log(
        from_agent,
        f"→ souther ({message_type}): {content[:120]}{'…' if len(content) > 120 else ''}",
        event_type="consult",
        task_id=task_id,
        details={
            "to": "souther",
            "from_agent": from_agent,
            "to_agent": "souther",
            "message_type": message_type,
            "preview": content[:200],
        },
    )

    reply = await _poll_reply(
        task_id=task_id,
        from_agent="souther",
        to_agent=from_agent,
        after_id=msg_id,
        message_type="approval",
    )
    if reply is None:
        return _text(
            f"ERROR: 社長から {CONSULT_TIMEOUT_S:.0f} 秒以内に応答がありませんでした。"
            "後で read_status で確認してください。"
        )
    return _text(f"社長からの裁定:\n\n{reply}")


async def _poll_reply(
    *,
    task_id: str,
    from_agent: str,
    to_agent: str,
    after_id: str,
    message_type: Optional[str],
) -> Optional[str]:
    store = get_store()
    elapsed = 0.0
    while elapsed < CONSULT_TIMEOUT_S:
        reply = await store.find_reply(
            task_id=task_id,
            from_agent=from_agent,
            to_agent=to_agent,
            after_id=after_id,
            message_type=message_type,
        )
        if reply:
            return reply["content"]
        await asyncio.sleep(POLL_INTERVAL_S)
        elapsed += POLL_INTERVAL_S
    return None


async def _handle_propose_plan(args: dict[str, Any]) -> list[TextContent]:
    task_id = args["task_id"]
    plan_json = args["plan_json"]
    try:
        json.loads(plan_json)
    except json.JSONDecodeError as e:
        return _text(f"ERROR: plan_json が不正な JSON: {e}")
    plan_id = await get_store().add_plan(task_id, plan_json)
    await log(
        "yuko",
        f"propose_plan 保存 (plan_id={plan_id[:8]})",
        event_type="plan",
        task_id=task_id,
    )
    return _text(f"計画を保存しました (plan_id={plan_id})。")


async def _handle_evaluate_deliverable(args: dict[str, Any]) -> list[TextContent]:
    task_id = args["task_id"]
    subtask_id = args["subtask_id"]
    evaluation = args["evaluation"]
    decision = args["decision"]
    round_ = int(args.get("round") or 0)

    valid = ("approve", "revise", "escalate_to_president")
    if decision not in valid:
        return _text(f"ERROR: decision は {valid} のいずれか。'{decision}' は不可。")

    store = get_store()

    auto_escalated = False
    if decision == "revise":
        prior = await store.count_revisions(subtask_id)
        if prior + 1 > MAX_REVISION_ROUNDS:
            decision = "escalate_to_president"
            auto_escalated = True

    rev_id = await store.add_revision(task_id, subtask_id, round_, evaluation, decision)
    # 評価対象の担当者を解決 (subtask の assigned_to)
    target_agent = await store.get_subtask_assignee(subtask_id) if hasattr(store, "get_subtask_assignee") else None
    await log(
        "yuko",
        f"evaluate (sub={subtask_id[:8]}, round={round_}, decision={decision})"
        + (" [自動escalate]" if auto_escalated else ""),
        event_type="evaluate",
        task_id=task_id,
        details={
            "decision": decision,
            "round": round_,
            "auto_escalated": auto_escalated,
            "target_agent": target_agent,
            "from_agent": "yuko",
            "to_agent": target_agent,
            "message_type": "evaluation",
        },
    )

    msg = f"評価記録 (rev_id={rev_id[:8]}, decision={decision})"
    if auto_escalated:
        msg += (
            f"\n注: 修正が上限 ({MAX_REVISION_ROUNDS}) を超過するため、自動的に "
            "escalate_to_president に変更されました。社長へ consult_souther を上申してください。"
        )
    elif decision == "revise":
        msg += (
            f"\n次のステップ: dispatch_task を呼び、subtask_id={subtask_id} と "
            f"revision_round={round_+1} を渡してください。"
        )
    elif decision == "approve":
        msg += "\n次のステップ: 後続工程または deliver へ。"
    elif decision == "escalate_to_president":
        msg += "\n次のステップ: consult_souther で社長へ approval_request を送ってください。"
    return _text(msg)


async def _handle_update_status(args: dict[str, Any]) -> list[TextContent]:
    task_id = args["task_id"]
    new_status = args["new_status"]
    notes = args.get("notes") or None
    await get_store().update_task_status(task_id, new_status, notes)
    await log(
        "system",
        f"task {task_id[:8]} → {new_status}",
        event_type="status_change",
        task_id=task_id,
        print_stdout=False,
    )
    return _text(f"案件 {task_id} を {new_status} に更新しました。")


async def _handle_read_status(args: dict[str, Any]) -> list[TextContent]:
    store = get_store()
    task_id = args.get("task_id") or ""
    if task_id:
        task = await store.get_task(task_id)
        if not task:
            return _text(f"案件 {task_id} は見つかりません。")
        subs = await store.list_subtasks(task_id)
        msgs = await store.list_messages(task_id)
        revs = await store.list_revisions(task_id)
        report = (
            f"# 案件 {task_id}\n"
            f"- title: {task['title']}\n"
            f"- status: {task['status']}\n"
            f"- assigned_to: {task['assigned_to']}\n"
            f"- description: {task['description']}\n\n"
            f"## subtasks ({len(subs)})\n"
        )
        for s in subs:
            report += f"  - [{s['status']}] {s['assigned_to']}: {s['description'][:80]}\n"
        report += f"\n## revisions ({len(revs)})\n"
        for r in revs:
            report += f"  - round={r['round']} sub={r['subtask_id'][:8]} {r['decision']}: {r['evaluation'][:60]}\n"
        report += f"\n## messages (直近10件 / 全{len(msgs)}件)\n"
        for m in msgs[-10:]:
            report += f"  - [{m['from_agent']}→{m['to_agent']}/{m['message_type']}] {m['content'][:80]}\n"
        return _text(report)
    else:
        tasks = await store.list_tasks()
        if not tasks:
            return _text("現在、案件はありません。")
        lines = ["# 全案件サマリ"]
        for t in tasks[:20]:
            lines.append(f"- [{t['status']}] {t['id'][:8]} {t['title']}")
        return _text("\n".join(lines))


async def _handle_deliver(args: dict[str, Any]) -> list[TextContent]:
    task_id = args["task_id"]
    delivery_message = args["delivery_message"]
    try:
        paths = json.loads(args["deliverable_paths_json"])
    except json.JSONDecodeError as e:
        return _text(f"ERROR: deliverable_paths_json が不正: {e}")

    store = get_store()
    for p in paths:
        await store.add_deliverable(task_id, p, "yuko", description="納品ファイル")
    await store.add_message("yuko", "client", delivery_message, "email", task_id)
    await store.update_task_status(task_id, "delivered")
    await log(
        "yuko",
        f"→ client: 納品完了 ({len(paths)} ファイル)",
        event_type="delivery",
        task_id=task_id,
        details={
            "from_agent": "yuko",
            "to_agent": "client",
            "message_type": "email",
            "subject": "📦 納品完了",
            "preview": delivery_message[:300],
            "deliverable_count": len(paths),
        },
    )
    return _text(f"納品完了。{len(paths)} ファイルをクライアントへ届けました。")


async def _handle_record_thought(args: dict[str, Any]) -> list[TextContent]:
    from_agent = args.get("from_agent") or ""
    text = (args.get("text") or "").strip()
    task_id = args.get("task_id") or None

    if from_agent != "yuko":
        return _text(f"ERROR: record_thought はユウコ専用。'{from_agent}' は使用不可。")
    if not text:
        return _text("ERROR: text が空です。")

    store = get_store()
    # 心のうちは messages テーブルに自分宛 (yuko→yuko) で type='thought' で投入
    msg_id = await store.add_message("yuko", "yuko", text, "thought", task_id)
    await log(
        "yuko",
        f"心のうち: {text[:120]}{'…' if len(text) > 120 else ''}",
        event_type="thought",
        task_id=task_id,
        details={
            "agent": "yuko",
            "from_agent": "yuko",
            "to_agent": "yuko",
            "message_type": "thought",
            "preview": text[:200],
        },
    )
    return _text(f"OK: 心のうちを記録しました (msg_id={msg_id[:8]})。")


_HANDLERS = {
    "send_message": _handle_send_message,
    "dispatch_task": _handle_dispatch_task,
    "consult_peer": _handle_consult_peer,
    "consult_souther": _handle_consult_souther,
    "propose_plan": _handle_propose_plan,
    "evaluate_deliverable": _handle_evaluate_deliverable,
    "update_status": _handle_update_status,
    "read_status": _handle_read_status,
    "deliver": _handle_deliver,
    "record_thought": _handle_record_thought,
}


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    handler = _HANDLERS.get(name)
    if handler is None:
        return _text(f"ERROR: 未知のツール '{name}'")
    try:
        return await handler(arguments or {})
    except Exception as e:  # noqa: BLE001 — MCP 経由で例外を文字列で返す
        return _text(f"ERROR: tool '{name}' が例外を投げました: {type(e).__name__}: {e}")


# ---------------------------------------------------------------------------
# stdio 起動
# ---------------------------------------------------------------------------


async def _main() -> None:
    # DB を確実に初期化 (WAL 化 + マイグレーション) しておく
    await get_store().init()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(_main())
