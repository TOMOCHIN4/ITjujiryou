"""カスタムツール定義 + SDK MCP サーバ。

社内ディスパッチ・横連携・品質ループの中核ロジックもここに集約。
ContextVar `_call_chain` で起動チェーンを追跡し、暴走を防ぐ。
"""
from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import Any, Optional

from claude_agent_sdk import create_sdk_mcp_server, tool

from src.agents.base import run_agent
from src.events.logger import log
from src.memory.store import get_store

REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUTS_DIR = REPO_ROOT / "outputs"

VALID_AGENTS = ("souther", "yuko", "designer", "engineer", "writer")
SUBORDINATES = ("designer", "engineer", "writer")

# 暴走防止パラメータ (env で上書き可)
MAX_CALL_DEPTH = 2  # yuko=0, subordinate=1, peer=2 まで
MAX_AGENT_CALLS = int(os.environ.get("ITJUJIRYOU_MAX_AGENT_CALLS", "30"))
MAX_CONSULT_PAIR = 2  # 同一 (from→to) ペアの consult 連続発火上限
MAX_REVISION_ROUNDS = int(os.environ.get("ITJUJIRYOU_MAX_REVISION_ROUNDS", "2"))

# 起動チェーン: [(agent_name, depth), ...]
_call_chain: ContextVar[list[tuple[str, int]]] = ContextVar("_call_chain", default=[])


def _ok(text: str) -> dict:
    return {"content": [{"type": "text", "text": text}]}


def current_depth() -> int:
    chain = _call_chain.get()
    return chain[-1][1] if chain else -1


def current_agent() -> Optional[str]:
    chain = _call_chain.get()
    return chain[-1][0] if chain else None


@asynccontextmanager
async def push_call(agent: str):
    """起動チェーンを push/pop する context manager。"""
    chain = list(_call_chain.get())
    new_depth = (chain[-1][1] + 1) if chain else 0
    chain.append((agent, new_depth))
    token = _call_chain.set(chain)
    try:
        yield new_depth
    finally:
        _call_chain.reset(token)


# --- send_message ----------------------------------------------------------
@tool(
    "send_message",
    "社内メンバー (souther/yuko/designer/engineer/writer) にメッセージを送る。"
    "to=souther で message_type=approval_request の場合、社長を起動して応答を返す。",
    {
        "to": str,
        "content": str,
        "task_id": str,
        "message_type": str,
        "from_agent": str,
    },
)
async def send_message_tool(args: dict[str, Any]) -> dict:
    to = args["to"]
    content = args["content"]
    task_id = args.get("task_id") or None
    message_type = args.get("message_type") or "report"
    from_agent = args.get("from_agent") or current_agent() or "unknown"

    if to not in VALID_AGENTS:
        return _ok(f"ERROR: 不正な宛先 '{to}'。有効値: {VALID_AGENTS}")

    store = get_store()
    await store.add_message(from_agent, to, content, message_type, task_id)
    await log(
        from_agent,
        f"→ {to} ({message_type}): {content[:120]}{'…' if len(content)>120 else ''}",
        event_type="message",
        task_id=task_id,
    )

    if to == "souther" and message_type in ("approval_request", "directive", "question"):
        # 案件起動回数の上限チェック
        if task_id and await store.count_agent_calls(task_id) >= MAX_AGENT_CALLS:
            return _ok(
                "ERROR: この案件のエージェント起動回数が上限に達しました。"
                "ユウコが自身の判断で進めるか、別案件として再分割してください。"
            )
        souther_input = (
            f"営業主任ユウコから以下の上申が届いた:\n\n"
            f"――――\n{content}\n――――\n\n"
            "サウザーとして応答してください。出力時の自己点検事項:\n"
            "- **時代背景**: 199X年核戦争後世界の人物として応答。江戸時代の将軍口調にならない\n"
            "- 一人称は「おれ」のみ（「私」「自分」は不可）\n"
            "- 自分を「社長」と呼ばない（自分は「聖帝」である）\n"
            "- 基本は1〜2文、一語で済むなら一語で（「ふん。許す」「却下」のみで完結 OK）\n"
            "- 自分の行動を実況・報告しない（「○○させます」「○○いたします」「○○へ伝達済み」等は不可）\n"
            "- 時代劇語彙は禁止（些事・沙汰・面妖・銭・謂れ・彫らせよ・断ち切れ・貫け・斬らせよ・斬り捨てよ・相成る 等）\n"
            "- 現代敬語・事務語（させていただく / 方針 / 対応 / 検討 / 対案 / 進行 等）は不可\n"
            "- 「ひかぬ媚びぬ省みぬ」「制圧前進あるのみ」は決定的場面のみ。日常承認では使わない\n"
            "- 「フ・・」「ふん」「・・・」「！！」「〜のだ！！」を必要に応じて織り込む"
        )
        async with push_call("souther"):
            souther_response = await run_agent(
                "souther", souther_input, _SERVER, task_id=task_id
            )
        await store.add_message("souther", from_agent, souther_response, "approval", task_id)
        await log(
            "souther",
            souther_response[:200] + ("…" if len(souther_response) > 200 else ""),
            event_type="message",
            task_id=task_id,
        )
        return _ok(f"社長より応答:\n{souther_response}")

    return _ok(f"{to} へメッセージを送りました。")


# --- dispatch_task ---------------------------------------------------------
@tool(
    "dispatch_task",
    "ユウコ専用。部下 (designer/engineer/writer) に構造化チケットでタスクを発注する。"
    "ticket_json には objective, requirements, success_criteria 等を含める。"
    "preceding_outputs_json で前工程の成果物を引き継げる ([{from, paths, summary}])。"
    "revision_round は修正サイクルの回次 (0=初回, 1=1回目修正, 2=2回目修正)。",
    {
        "assigned_to": str,
        "task_id": str,
        "ticket_json": str,
        "preceding_outputs_json": str,
        "revision_round": int,
        "subtask_id": str,  # 修正時は同一 subtask の継続として渡す
    },
)
async def dispatch_task_tool(args: dict[str, Any]) -> dict:
    assigned_to = args["assigned_to"]
    task_id = args["task_id"]
    ticket_json = args["ticket_json"]
    preceding_outputs_json = args.get("preceding_outputs_json") or "[]"
    revision_round = int(args.get("revision_round") or 0)
    explicit_subtask_id = args.get("subtask_id") or None

    if assigned_to not in SUBORDINATES:
        return _ok(f"ERROR: 部下は {SUBORDINATES} のいずれか。'{assigned_to}' は不可。")

    try:
        ticket = json.loads(ticket_json)
    except json.JSONDecodeError as e:
        return _ok(f"ERROR: ticket_json が不正な JSON: {e}")
    try:
        preceding = json.loads(preceding_outputs_json)
        if not isinstance(preceding, list):
            preceding = []
    except json.JSONDecodeError:
        preceding = []

    store = get_store()

    # 案件起動回数の上限チェック
    if await store.count_agent_calls(task_id) >= MAX_AGENT_CALLS:
        return _ok(
            "ERROR: この案件のエージェント起動回数が上限に達しました。"
            "ユウコは自身で着地点を判断するか、社長へ escalate してください。"
        )

    # 修正サイクル上限チェック
    if explicit_subtask_id and revision_round > MAX_REVISION_ROUNDS:
        return _ok(
            f"ERROR: 修正回数が上限 ({MAX_REVISION_ROUNDS}) を超過。"
            f"これ以上の revise は禁止。社長へ escalate_to_president を上申してください。"
        )

    sub_id = explicit_subtask_id or await store.create_subtask(
        task_id, assigned_to, ticket.get("objective", "")[:500]
    )
    await log(
        "yuko",
        f"dispatch_task → {assigned_to} (sub={sub_id[:8]}, round={revision_round})",
        event_type="dispatch",
        task_id=task_id,
        details={"assigned_to": assigned_to, "subtask_id": sub_id, "round": revision_round},
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

    subordinate_input = (
        "営業主任ユウコより、以下の構造化チケットを受領しました。\n\n"
        f"案件ID: {task_id}\n"
        f"サブタスクID: {sub_id}\n"
        f"成果物保存先: outputs/{task_id}/\n"
        f"{round_note}"
        f"{preceding_block}\n"
        "--- チケット (JSON) ---\n"
        f"{json.dumps(ticket, ensure_ascii=False, indent=2)}\n"
        "----------------------\n\n"
        "memory ディレクトリ (data/memory/" + assigned_to + "/) を確認し、"
        "成果物を outputs/" + task_id + "/ に保存してください。"
        "完了したら、ユウコへの完了報告を本文として返答してください。"
    )

    async with push_call(assigned_to):
        response = await run_agent(assigned_to, subordinate_input, _SERVER, task_id=task_id)
    if revision_round == 0:
        await store.complete_subtask(sub_id, str(out_dir))
    await store.add_message(assigned_to, "yuko", response, "report", task_id)
    await log(
        assigned_to,
        f"完了報告 → yuko: {response[:160]}{'…' if len(response)>160 else ''}",
        event_type="report",
        task_id=task_id,
    )
    return _ok(f"{assigned_to} の完了報告 (sub={sub_id[:8]}, round={revision_round}):\n\n{response}")


# --- consult_peer ----------------------------------------------------------
@tool(
    "consult_peer",
    "部下 (designer/engineer/writer) のみ使用可。隣の部下に専門相談を投げ、"
    "同期的に応答を得る。雑談禁止、技術判断のみ。",
    {
        "to": str,
        "task_id": str,
        "question": str,
        "context": str,
        "from_agent": str,
    },
)
async def consult_peer_tool(args: dict[str, Any]) -> dict:
    to = args["to"]
    task_id = args["task_id"]
    question = args["question"]
    context = args.get("context") or ""
    from_agent = args.get("from_agent") or current_agent() or "unknown"

    # 権限チェック (発信側が部下であること)
    if from_agent not in SUBORDINATES:
        return _ok(f"ERROR: consult_peer は部下専用。'{from_agent}' は使用不可。")
    if to not in SUBORDINATES:
        return _ok(f"ERROR: 相談相手は部下のみ。'{to}' は不可。")
    if to == from_agent:
        return _ok("ERROR: 自分自身に相談はできません。")

    # 深さチェック
    depth = current_depth()
    if depth >= MAX_CALL_DEPTH:
        return _ok(
            f"ERROR: 起動チェーン深度が上限 ({MAX_CALL_DEPTH}) に達しています "
            f"(現在 depth={depth})。これ以上の入れ子相談は不可。"
            "あなた自身で判断するか、ユウコに上申してください。"
        )

    store = get_store()

    # ピンポン上限チェック
    pair_count = await store.count_consult_pair(task_id, from_agent, to)
    if pair_count >= MAX_CONSULT_PAIR:
        return _ok(
            f"ERROR: {from_agent}→{to} の相談回数が上限 ({MAX_CONSULT_PAIR}) を超過。"
            "これ以上同じ相手への相談は不可。あなた自身で決めるか、ユウコに上申してください。"
        )

    # 案件起動回数の上限チェック
    if await store.count_agent_calls(task_id) >= MAX_AGENT_CALLS:
        return _ok(
            "ERROR: この案件のエージェント起動回数が上限に達しました。"
            "あなた自身で判断してください。"
        )

    consult_message = (
        f"【相談】{from_agent}より、技術的な相談が届きました。\n"
        f"案件ID: {task_id}\n\n"
        f"--- 相談内容 ---\n{question}\n----------------\n"
        + (f"\n--- 背景・補足 ---\n{context}\n----------------\n" if context else "")
        + "\nあなたの専門知識から簡潔に応答してください (本回答が同期的に相談者へ返ります)。"
    )

    await store.add_message(from_agent, to, question, "consult", task_id)
    await log(
        from_agent,
        f"→ {to} (consult): {question[:120]}{'…' if len(question)>120 else ''}",
        event_type="consult",
        task_id=task_id,
        details={"to": to, "depth": depth + 1},
    )

    async with push_call(to):
        response = await run_agent(to, consult_message, _SERVER, task_id=task_id)

    await store.add_message(to, from_agent, response, "consult_reply", task_id)
    await log(
        to,
        f"→ {from_agent} (consult_reply): {response[:160]}{'…' if len(response)>160 else ''}",
        event_type="consult_reply",
        task_id=task_id,
    )
    return _ok(f"{to} からの応答:\n\n{response}")


# --- propose_plan ----------------------------------------------------------
@tool(
    "propose_plan",
    "ユウコ専用。案件の初期計画を保存する。複合案件・規模中以上で必須。"
    "plan_json は {steps:[{step,assignee,deps,quality_criteria}], risks, milestones} 等。",
    {"task_id": str, "plan_json": str},
)
async def propose_plan_tool(args: dict[str, Any]) -> dict:
    task_id = args["task_id"]
    plan_json = args["plan_json"]
    try:
        json.loads(plan_json)
    except json.JSONDecodeError as e:
        return _ok(f"ERROR: plan_json が不正な JSON: {e}")
    plan_id = await get_store().add_plan(task_id, plan_json)
    await log(
        "yuko",
        f"propose_plan 保存 (plan_id={plan_id[:8]})",
        event_type="plan",
        task_id=task_id,
    )
    return _ok(f"計画を保存しました (plan_id={plan_id})。社長への上申本文に要約を含めてください。")


# --- evaluate_deliverable --------------------------------------------------
@tool(
    "evaluate_deliverable",
    "ユウコ専用。部下成果物の品質判定。decision は approve/revise/escalate_to_president。"
    "revise を返した場合、必ず再 dispatch_task で revision_round を +1 して同一 subtask_id を渡すこと。",
    {
        "task_id": str,
        "subtask_id": str,
        "evaluation": str,
        "decision": str,
        "round": int,
    },
)
async def evaluate_deliverable_tool(args: dict[str, Any]) -> dict:
    task_id = args["task_id"]
    subtask_id = args["subtask_id"]
    evaluation = args["evaluation"]
    decision = args["decision"]
    round_ = int(args.get("round") or 0)

    valid = ("approve", "revise", "escalate_to_president")
    if decision not in valid:
        return _ok(f"ERROR: decision は {valid} のいずれか。'{decision}' は不可。")

    store = get_store()

    # 修正上限の自動降格: revise を希望しても上限超なら escalate に強制変更
    auto_escalated = False
    if decision == "revise":
        prior = await store.count_revisions(subtask_id)
        if prior + 1 > MAX_REVISION_ROUNDS:
            decision = "escalate_to_president"
            auto_escalated = True

    rev_id = await store.add_revision(task_id, subtask_id, round_, evaluation, decision)
    await log(
        "yuko",
        f"evaluate (sub={subtask_id[:8]}, round={round_}, decision={decision})"
        + (" [自動escalate]" if auto_escalated else ""),
        event_type="evaluate",
        task_id=task_id,
        details={"decision": decision, "round": round_, "auto_escalated": auto_escalated},
    )

    msg = f"評価記録 (rev_id={rev_id[:8]}, decision={decision})"
    if auto_escalated:
        msg += (
            f"\n注: 修正が上限 ({MAX_REVISION_ROUNDS}) を超過するため、自動的に "
            "escalate_to_president に変更されました。社長へ approval_request を上申してください。"
        )
    elif decision == "revise":
        msg += f"\n次のステップ: dispatch_task を呼び、subtask_id={subtask_id} と revision_round={round_+1} を渡してください。"
    elif decision == "approve":
        msg += "\n次のステップ: 後続工程または deliver へ。"
    elif decision == "escalate_to_president":
        msg += "\n次のステップ: send_message で社長へ approval_request を送ってください。"
    return _ok(msg)


# --- update_status ---------------------------------------------------------
@tool(
    "update_status",
    "案件の状態を更新する (received / hearing / approved / in_progress / review / "
    "delivered / cancelled)。",
    {"task_id": str, "new_status": str, "notes": str},
)
async def update_status_tool(args: dict[str, Any]) -> dict:
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
    return _ok(f"案件 {task_id} を {new_status} に更新しました。")


# --- read_status -----------------------------------------------------------
@tool(
    "read_status",
    "案件の状態と関連情報を閲覧する。task_id を指定しなければ全件サマリ。",
    {"task_id": str},
)
async def read_status_tool(args: dict[str, Any]) -> dict:
    store = get_store()
    task_id = args.get("task_id") or ""
    if task_id:
        task = await store.get_task(task_id)
        if not task:
            return _ok(f"案件 {task_id} は見つかりません。")
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
        report += f"\n## messages (直近5件 / 全{len(msgs)}件)\n"
        for m in msgs[-5:]:
            report += f"  - [{m['from_agent']}→{m['to_agent']}/{m['message_type']}] {m['content'][:80]}\n"
        return _ok(report)
    else:
        tasks = await store.list_tasks()
        if not tasks:
            return _ok("現在、案件はありません。")
        lines = ["# 全案件サマリ"]
        for t in tasks[:20]:
            lines.append(f"- [{t['status']}] {t['id'][:8]} {t['title']}")
        return _ok("\n".join(lines))


# --- deliver ---------------------------------------------------------------
@tool(
    "deliver",
    "ユウコ専用。クライアントへの納品を行う。納品メール本文と成果物パスを記録。",
    {
        "task_id": str,
        "deliverable_paths_json": str,
        "delivery_message": str,
    },
)
async def deliver_tool(args: dict[str, Any]) -> dict:
    task_id = args["task_id"]
    delivery_message = args["delivery_message"]
    try:
        paths = json.loads(args["deliverable_paths_json"])
    except json.JSONDecodeError as e:
        return _ok(f"ERROR: deliverable_paths_json が不正: {e}")

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
    )
    return _ok(f"納品完了。{len(paths)} ファイルをクライアントへ届けました。")


# --- MCP サーバ ------------------------------------------------------------
_SERVER = create_sdk_mcp_server(
    name="itjujiryou",
    version="0.2.0",
    tools=[
        send_message_tool,
        dispatch_task_tool,
        consult_peer_tool,
        propose_plan_tool,
        evaluate_deliverable_tool,
        update_status_tool,
        read_status_tool,
        deliver_tool,
    ],
)


def get_mcp_server():
    return _SERVER
