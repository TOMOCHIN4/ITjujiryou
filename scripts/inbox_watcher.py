#!/usr/bin/env python3
"""愛帝十字陵 inbox watcher。

SQLite messages を 1 秒ごとに polling し、delivered_at が NULL の行を該当
エージェントの tmux pane に `tmux send-keys` で投入する。

Phase A は 2 エージェント (souther, yuko) のみ対応。Phase B で 5 人に拡張する。

pane の対応は環境変数で上書き可:
  ITJ_PANE_SOUTHER (default: itj:office.0)
  ITJ_PANE_YUKO    (default: itj:office.1)
  ...

注意: 現状は pane の idle 判定をしていない。Claude Code が他作業中の pane に
send-keys すると割り込むため、Phase A では「同時並行発注はしない」運用とする。
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.memory.store import get_store  # noqa: E402

POLL_INTERVAL = float(os.environ.get("ITJ_WATCHER_POLL_INTERVAL", "1.0"))

# --- curator scheduler 設定 (PLAN.md「サザン二重構造 未配線 3 operation」対応) ---
# cron-based 発火 (cross_review / archive_judge) の周期と検査間隔を環境変数で上書き可。
CROSS_REVIEW_INTERVAL_DAYS = int(os.environ.get("ITJ_CROSS_REVIEW_INTERVAL_DAYS", "30"))
ARCHIVE_JUDGE_INTERVAL_DAYS = int(os.environ.get("ITJ_ARCHIVE_JUDGE_INTERVAL_DAYS", "90"))
SCHEDULE_CHECK_INTERVAL_SEC = int(
    os.environ.get("ITJ_CURATOR_SCHEDULE_CHECK_INTERVAL_SEC", "3600")
)

# cross_review の検査対象 category (data/memory/company/{category}/)
CROSS_REVIEW_CATEGORIES = [
    "client_profile",
    "quality_bar",
    "workflow_rule",
    "recurring_pattern",
]
# archive_judge の検査対象 role (data/memory/{role}/_scratch/)
ARCHIVE_JUDGE_ROLES = ["writer", "designer", "engineer", "yuko"]

CURATOR_SCHEDULE_PATH = (
    REPO_ROOT / "data" / "memory" / "company" / "_curator_schedule.json"
)

PANE_MAP = {
    "souther": os.environ.get("ITJ_PANE_SOUTHER", "itj:office.0"),
    "yuko": os.environ.get("ITJ_PANE_YUKO", "itj:office.1"),
    "designer": os.environ.get("ITJ_PANE_DESIGNER", "itj:office.2"),
    "engineer": os.environ.get("ITJ_PANE_ENGINEER", "itj:office.3"),
    "writer": os.environ.get("ITJ_PANE_WRITER", "itj:office.4"),
}


def _pane_for(agent: str) -> str:
    return PANE_MAP.get(agent, "")


def tmux_send(pane: str, text: str) -> None:
    """pane に文字列を流し込み Enter で turn を開始させる。

    Claude Code TUI は paste-buffer された複数行を multi-line input として扱うため、
    1 回の Enter は改行扱いで turn が開始しない。2 回目の Enter で確定する経験則。
    """
    try:
        proc = subprocess.run(
            ["tmux", "load-buffer", "-"], input=text, text=True, check=False
        )
        if proc.returncode != 0:
            return
        subprocess.run(["tmux", "paste-buffer", "-d", "-t", pane], check=False)
        # 1 つ目の Enter は multi-line 入力の最終行を確定するため
        subprocess.run(["tmux", "send-keys", "-t", pane, "Enter"], check=False)
        # 2 つ目の Enter で turn を開始 (Claude Code は空行 Enter で submit)
        time.sleep(0.15)
        subprocess.run(["tmux", "send-keys", "-t", pane, "Enter"], check=False)
    except FileNotFoundError:
        print("[watcher] tmux command not found", file=sys.stderr)


def format_prompt(msg: dict) -> str:
    content = msg["content"]
    task_id = msg.get("task_id") or ""
    return (
        f"新着メッセージ (msg_id={msg['id']}):\n"
        f"  from: {msg['from_agent']}\n"
        f"  type: {msg['message_type']}\n"
        f"  task_id: {task_id}\n"
        "---\n"
        f"{content}\n"
        "---\n"
        "このメッセージに対応してください。"
    )


# 裏側 silent モードへのトリガー sentinel。inject_souther_mode.py が prompt 先頭に
# これを見つけたら Omage Gate を skip し、memory-curator subagent 起動経路に乗せる。
BACKSTAGE_CURATOR_TAG = "[BACKSTAGE:curator]"


def format_backstage_curator_prompt(msg: dict) -> str:
    """curator_request を souther pane に投入する裏側プロンプト。

    `format_prompt` と同じ構造だが先頭に `BACKSTAGE_CURATOR_TAG` を付加し、
    末尾の指示文を memory-curator subagent 起動向けに差し替えている。
    """
    content = msg["content"]
    task_id = msg.get("task_id") or ""
    return (
        f"{BACKSTAGE_CURATOR_TAG}\n"
        f"新着メッセージ (msg_id={msg['id']}):\n"
        f"  from: {msg['from_agent']}\n"
        f"  type: {msg['message_type']}\n"
        f"  task_id: {task_id}\n"
        "---\n"
        f"{content}\n"
        "---\n"
        "裏側で memory-curator subagent を起動して処理し、"
        "curator_response でユウコへ通知してください。"
    )


# ---------------------------------------------------------------------------
# 記憶整理フロー (SPEC.md §10.2-10.3)
# ---------------------------------------------------------------------------


def format_scratch_consolidation_prompt(task_id: str, role: str) -> str:
    """post_deliver_trigger event を受けて、各 role pane に投入する整理指示。"""
    case_short = (task_id or "")[:8]
    return (
        f"[整理フロー] 案件 {case_short} が delivered になりました。\n"
        f"`data/memory/{role}/_scratch/{task_id}/` を memory-search subagent 経由で読み、以下を行ってください:\n\n"
        f"1. 自分の個人記憶に昇格すべき知見:\n"
        f"   該当 topic フォルダのファイルへ追記 / 新規作成 (frontmatter 必須、schema: personal-memory/v1)\n\n"
        f"2. 会社記憶へ昇格すべき知見:\n"
        f"   `data/memory/{role}/_proposals/{task_id}.md` を Write (schema: proposal/v1, proposed_for: company)\n"
        f"   作成した場合のみ、ユウコへ:\n"
        f"     send_message(to=\"yuko\", message_type=\"memory_proposal\", task_id=\"{task_id}\",\n"
        f"                  content=\"提案 ready: data/memory/{role}/_proposals/{task_id}.md\")\n\n"
        f"3. scratch は削除せず温存 (将来のアーカイブで処理する)\n\n"
        "完了後「整理完了」と短く返してください。"
    )


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slugify(text: str) -> str:
    s = re.sub(r"[^A-Za-z0-9_\-]+", "-", (text or "").strip()).strip("-").lower()
    return s or "untitled"


def _parse_proposal_frontmatter(content: str) -> dict:
    """proposal/v1 frontmatter (YAML) を簡易パース。aiosqlite と違って小さく済ませる。
    PyYAML がなくても動くよう、key: value / key: [a, b, c] の 2 形式のみ拾う。"""
    m = re.match(r"\A---\s*\n(.*?)\n---\s*\n?", content, re.DOTALL)
    if not m:
        return {}
    body = m.group(1)
    out: dict = {}
    for line in body.splitlines():
        if ":" not in line:
            continue
        k, _, v = line.partition(":")
        k = k.strip()
        v = v.strip()
        if v.startswith("[") and v.endswith("]"):
            items = [x.strip().strip("'\"") for x in v[1:-1].split(",")]
            out[k] = [x for x in items if x]
        else:
            out[k] = v.strip("'\"")
    return out


def _proposal_body_after_frontmatter(content: str) -> str:
    m = re.match(r"\A---\s*\n.*?\n---\s*\n?(.*)\Z", content, re.DOTALL)
    return m.group(1) if m else content


def _company_target_path(category: str, slug: str) -> Path:
    """data/memory/company/{category}/{slug}.md の絶対パスを返す。"""
    return (
        REPO_ROOT / "data" / "memory" / "company" / category / f"{slug}.md"
    )


# ---------------------------------------------------------------------------
# curator スケジューラ (PLAN.md「サザン二重構造 4 op 中の未配線 3 つ」対応)
#   - cross_review:  watcher 内蔵 cron で N 日経過した company/{category}/ に対し発火
#   - archive_judge: watcher 内蔵 cron で N 日経過した {role}/_scratch/ に対し発火
#   - client_profile_maintenance: ユウコ手動トリガー (workflow.md に作法あり、ここでは扱わない)
#
# どの cron 発火も `curator_trigger` メッセージを yuko に投入し、
# 既存 `curator_request` 経路 (yuko → souther backstage → memory-curator subagent) へ
# 接続する。yuko 側 workflow.md がトリガーを受領→ consult_souther でブリッジする。
# ---------------------------------------------------------------------------


def _load_curator_schedule() -> dict:
    """`_curator_schedule.json` を読む。存在しない/破損時は空 dict。"""
    if not CURATOR_SCHEDULE_PATH.exists():
        return {}
    try:
        return json.loads(CURATOR_SCHEDULE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_curator_schedule(state: dict) -> None:
    CURATOR_SCHEDULE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CURATOR_SCHEDULE_PATH.write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _parse_iso_dt(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s)
    except (TypeError, ValueError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def select_overdue_target(
    state_section: dict,
    candidates: list[str],
    interval_days: int,
    now: datetime,
) -> Optional[str]:
    """state_section[name] = last_run_iso の dict から、interval_days 以上経過した
    候補のうち最古を返す。一度も走っていない (None / 不正) ものは最優先扱い。"""
    overdue: list[tuple[str, datetime]] = []
    epoch = datetime.min.replace(tzinfo=timezone.utc)
    for name in candidates:
        last = _parse_iso_dt(state_section.get(name))
        if last is None:
            overdue.append((name, epoch))
            continue
        if (now - last) >= timedelta(days=interval_days):
            overdue.append((name, last))
    if not overdue:
        return None
    overdue.sort(key=lambda x: x[1])
    return overdue[0][0]


def build_curator_trigger_content(
    operation: str, case_id: str, params: dict
) -> str:
    """yuko に投入する curator_trigger 本文を整形。yuko 側がパースして
    consult_souther(curator_request, refs=...) を組み立てる。"""
    lines = [
        "[curator_trigger]",
        f"operation={operation}",
        f"case_id={case_id}",
    ]
    for k, v in params.items():
        lines.append(f"{k}={v}")
    lines.append("")
    lines.append(
        "上記 operation で memory-curator subagent をサザンへ依頼してください "
        "(consult_souther message_type=curator_request, refs={operation, "
        "case_id, ...}) 。詳細は workflow.md §「curator_trigger 受領時」参照。"
    )
    return "\n".join(lines)


async def maybe_fire_scheduled_curator_triggers(
    store, now: Optional[datetime] = None
) -> list[dict]:
    """schedule.json を読み、cross_review / archive_judge で interval を超えた
    最古 target に対し `curator_trigger` を yuko に 1 件投入する (op ごとに 1 件)。

    返り値: 発火したトリガーの dict のリスト (テスト用 / ログ出力用)。
    """
    if now is None:
        now = datetime.now(timezone.utc)
    state = _load_curator_schedule()
    fired: list[dict] = []
    today_date = now.strftime("%Y-%m-%d")

    # --- cross_review: 最古の overdue category を 1 件 ---
    cross_state = state.setdefault("cross_review", {})
    target_cat = select_overdue_target(
        cross_state, CROSS_REVIEW_CATEGORIES, CROSS_REVIEW_INTERVAL_DAYS, now
    )
    if target_cat:
        case_id = f"cross-review-{target_cat}-{today_date}"
        content = build_curator_trigger_content(
            "cross_review", case_id, {"target_category": target_cat}
        )
        await store.add_message(
            from_agent="system",
            to_agent="yuko",
            content=content,
            message_type="curator_trigger",
            task_id=case_id,
        )
        cross_state[target_cat] = now.isoformat()
        fired.append(
            {"operation": "cross_review", "target": target_cat, "case_id": case_id}
        )

    # --- archive_judge: 最古の overdue role を 1 件 ---
    archive_state = state.setdefault("archive_judge", {})
    target_role = select_overdue_target(
        archive_state, ARCHIVE_JUDGE_ROLES, ARCHIVE_JUDGE_INTERVAL_DAYS, now
    )
    if target_role:
        cutoff_iso = (now - timedelta(days=ARCHIVE_JUDGE_INTERVAL_DAYS)).isoformat()
        case_id = f"archive-judge-{target_role}-{today_date}"
        content = build_curator_trigger_content(
            "archive_judge",
            case_id,
            {"target_role": target_role, "cutoff_iso": cutoff_iso},
        )
        await store.add_message(
            from_agent="system",
            to_agent="yuko",
            content=content,
            message_type="curator_trigger",
            task_id=case_id,
        )
        archive_state[target_role] = now.isoformat()
        fired.append(
            {"operation": "archive_judge", "target": target_role, "case_id": case_id}
        )

    if fired:
        _save_curator_schedule(state)
    return fired


async def process_memory_approval(msg: dict) -> dict:
    """sazan → yuko の memory_approval を受領して会社記憶を物理反映する。

    返り値: 反映結果のサマリ dict (テスト用)。"""
    store = get_store()
    task_id = msg.get("task_id") or ""
    content = msg.get("content") or ""

    # 却下系の文言なら何もしない (ユウコが proposal を消すだけ)
    if any(token in content for token in ("却下", "未熟", "下郎の戯言")):
        return {"action": "rejected", "task_id": task_id}

    proposal_path = (
        REPO_ROOT
        / "data"
        / "memory"
        / "company"
        / "_proposals"
        / f"{task_id}.md"
    )
    if not proposal_path.exists():
        print(
            f"[watcher] memory_approval: proposal not found at {proposal_path}",
            file=sys.stderr,
        )
        return {"action": "skipped", "reason": "proposal_missing", "task_id": task_id}

    raw = proposal_path.read_text(encoding="utf-8")
    fm = _parse_proposal_frontmatter(raw)
    body = _proposal_body_after_frontmatter(raw)

    category = fm.get("target_category") or fm.get("category") or "recurring_pattern"
    slug = fm.get("target_slug") or _slugify(fm.get("case_type") or task_id[:8])
    target = _company_target_path(category, slug)
    target.parent.mkdir(parents=True, exist_ok=True)

    # 既存ファイルがあれば追記 (見出しで境界を作る)、無ければ新規 (frontmatter 付き)
    if target.exists():
        existing = target.read_text(encoding="utf-8")
        appendix = (
            f"\n\n---\n\n## {fm.get('case_type') or task_id[:8]} ({task_id})\n\n"
            f"{body.strip()}\n"
        )
        target.write_text(existing + appendix, encoding="utf-8")
    else:
        contributors = fm.get("contributors") or []
        contributors_yaml = (
            "[" + ", ".join(contributors) + "]" if contributors else "[]"
        )
        case_ids_yaml = "[" + (fm.get("case_id") or task_id) + "]"
        head = (
            "---\n"
            "schema: company-memory/v1\n"
            f"category: {category}\n"
            f"case_ids: {case_ids_yaml}\n"
            f"contributors: {contributors_yaml}\n"
            f"approved_at: {_now_iso()}\n"
            "approved_by: souther\n"
            f"keywords: {fm.get('keywords') or '[]'}\n"
            "---\n\n"
            f"{body.strip()}\n"
        )
        target.write_text(head, encoding="utf-8")

    # _last_write.log に JSONL 追記
    log_path = REPO_ROOT / "data" / "memory" / "company" / "_last_write.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.touch(exist_ok=True)
    entry = {
        "timestamp": _now_iso(),
        "task_id": task_id,
        "approval_msg_id": msg.get("id"),
        "proposal_path": str(proposal_path.relative_to(REPO_ROOT)),
        "written_path": str(target.relative_to(REPO_ROOT)),
        "category": category,
        "contributors": fm.get("contributors") or [],
    }
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # _proposals/_archived/ に移送
    archived = (
        REPO_ROOT
        / "data"
        / "memory"
        / "company"
        / "_proposals"
        / "_archived"
        / f"{task_id}.md"
    )
    archived.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(proposal_path), str(archived))

    # ユウコへ memory_finalized 通知
    finalized_id = await store.add_message(
        from_agent="system",
        to_agent="yuko",
        content=(
            f"会社記憶確定: {target.relative_to(REPO_ROOT)}\n"
            f"(category={category}, slug={slug})"
        ),
        message_type="memory_finalized",
        task_id=task_id,
    )

    return {
        "action": "finalized",
        "task_id": task_id,
        "written_path": str(target.relative_to(REPO_ROOT)),
        "category": category,
        "slug": slug,
        "finalized_msg_id": finalized_id,
    }


async def main() -> None:
    store = get_store()
    await store.init()
    print(
        f"[watcher] start. poll={POLL_INTERVAL}s pane_map={ {k:v for k,v in PANE_MAP.items() if v} }"
    )
    # curator scheduler の前回チェック monotonic ts (起動時は 0 = 初回 iter で実行)
    last_schedule_check_mono: float = 0.0
    while True:
        t0 = time.monotonic()
        try:
            msgs = await store.fetch_undelivered_messages()
        except Exception as e:  # noqa: BLE001
            print(f"[watcher] fetch error: {e}", file=sys.stderr)
            await asyncio.sleep(POLL_INTERVAL)
            continue

        for m in msgs:
            to = m["to_agent"]
            mtype = m.get("message_type") or ""
            from_a = m.get("from_agent") or ""
            # client 宛は WS ダッシュボード経由で人間に見せる。watcher は配信スキップ
            if to == "client":
                await store.mark_delivered(m["id"])
                continue
            # サザン → ユウコ memory_approval は通常配信に加え会社記憶への物理反映を行う
            if mtype == "memory_approval" and from_a == "souther" and to == "yuko":
                try:
                    result = await process_memory_approval(m)
                    print(
                        f"[watcher] memory_approval processed: {result.get('action')} "
                        f"task={m.get('task_id') or ''[:8]}"
                    )
                except Exception as e:  # noqa: BLE001
                    print(
                        f"[watcher] memory_approval error: {e}",
                        file=sys.stderr,
                    )
            pane = _pane_for(to)
            if not pane:
                # 未配置の宛先 (Phase A では designer/engineer/writer は不在)
                print(
                    f"[watcher] no pane for {to}; leaving msg={m['id'][:8]} "
                    "(will be picked up after pane is added)"
                )
                continue
            # 裏側 silent モード: curator_request to souther は sentinel 付きで送る
            if to == "souther" and mtype == "curator_request":
                prompt = format_backstage_curator_prompt(m)
                marker = "BACKSTAGE"
            else:
                prompt = format_prompt(m)
                marker = ""
            tmux_send(pane, prompt)
            await store.mark_delivered(m["id"])
            tag = f" [{marker}]" if marker else ""
            print(
                f"[watcher] -> {to:<8s} ({m['message_type']:<16s}) msg={m['id'][:8]} pane={pane}{tag}"
            )

        # post_deliver_trigger events を処理 (各 role pane に scratch 整理指示を投入)
        try:
            events = await store.fetch_unprocessed_events("post_deliver_trigger")
        except Exception as e:  # noqa: BLE001
            print(f"[watcher] event fetch error: {e}", file=sys.stderr)
            events = []
        for ev in events:
            task_id = ev.get("task_id") or ""
            roles = (ev.get("details") or {}).get("roles") or [
                "writer",
                "designer",
                "engineer",
                "yuko",
            ]
            for role in roles:
                pane = _pane_for(role)
                if not pane:
                    continue
                prompt = format_scratch_consolidation_prompt(task_id, role)
                tmux_send(pane, prompt)
                print(
                    f"[watcher] post_deliver -> {role:<8s} event={ev['id']} task={task_id[:8]}"
                )
            await store.mark_event_processed(int(ev["id"]))

        # --- curator scheduler (SCHEDULE_CHECK_INTERVAL_SEC 毎、起動直後は即発火) ---
        if (
            last_schedule_check_mono == 0.0
            or time.monotonic() - last_schedule_check_mono >= SCHEDULE_CHECK_INTERVAL_SEC
        ):
            try:
                fired = await maybe_fire_scheduled_curator_triggers(store)
                for f in fired:
                    print(
                        f"[watcher] curator scheduler fired: op={f['operation']} "
                        f"target={f['target']} case_id={f['case_id']}"
                    )
            except Exception as e:  # noqa: BLE001
                print(f"[watcher] curator scheduler error: {e}", file=sys.stderr)
            last_schedule_check_mono = time.monotonic()

        elapsed = time.monotonic() - t0
        await asyncio.sleep(max(0.0, POLL_INTERVAL - elapsed))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("[watcher] bye")
