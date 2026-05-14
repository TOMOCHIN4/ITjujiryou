-- 案件
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    status TEXT NOT NULL,
    client_request TEXT,
    structured_ticket TEXT,
    assigned_to TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    completed_at TEXT,
    deadline TEXT
);

CREATE TABLE IF NOT EXISTS subtasks (
    id TEXT PRIMARY KEY,
    parent_task_id TEXT NOT NULL REFERENCES tasks(id),
    assigned_to TEXT NOT NULL,
    description TEXT NOT NULL,
    status TEXT NOT NULL,
    deliverable_path TEXT,
    created_at TEXT NOT NULL,
    completed_at TEXT
);

CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    task_id TEXT REFERENCES tasks(id),
    from_agent TEXT NOT NULL,
    to_agent TEXT NOT NULL,
    content TEXT NOT NULL,
    message_type TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    delivered_at TEXT
);

CREATE TABLE IF NOT EXISTS deliverables (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL REFERENCES tasks(id),
    file_path TEXT NOT NULL,
    file_type TEXT,
    created_by TEXT NOT NULL,
    description TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    agent TEXT NOT NULL,
    event_type TEXT NOT NULL,
    task_id TEXT REFERENCES tasks(id),
    details TEXT,
    parent_event_id INTEGER REFERENCES events(id),
    processed_at TEXT
);

-- 初期計画 (Phase 1.5)
CREATE TABLE IF NOT EXISTS plans (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL REFERENCES tasks(id),
    version INTEGER NOT NULL,
    plan_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

-- 修正サイクル記録 (Phase 1.5)
CREATE TABLE IF NOT EXISTS revisions (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL REFERENCES tasks(id),
    subtask_id TEXT NOT NULL,
    round INTEGER NOT NULL,
    evaluation TEXT NOT NULL,
    decision TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_messages_task ON messages(task_id);
CREATE INDEX IF NOT EXISTS idx_messages_undelivered
    ON messages(delivered_at) WHERE delivered_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_events_task ON events(task_id);
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);
CREATE INDEX IF NOT EXISTS idx_events_parent ON events(parent_event_id);
CREATE INDEX IF NOT EXISTS idx_events_unprocessed
    ON events(event_type, processed_at) WHERE processed_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_plans_task ON plans(task_id);
CREATE INDEX IF NOT EXISTS idx_revisions_task ON revisions(task_id);
CREATE INDEX IF NOT EXISTS idx_revisions_subtask ON revisions(subtask_id);
