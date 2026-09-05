-- BOOT1.3 — tables exist; rows filled by AUTH / SYNC.
-- Single mailbox in v1 (mailbox_account.id = 1).

CREATE TABLE IF NOT EXISTS mailbox_account (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    display_name TEXT,
    graph_user_id TEXT,
    encrypted_access_token BLOB,
    encrypted_refresh_token BLOB,
    token_expires_at TEXT,
    mailbox_user TEXT,
    mailbox_password_hash TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sync_session (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT NOT NULL,
    error TEXT,
    celery_task_id TEXT,
    messages_tossed INTEGER NOT NULL DEFAULT 0,
    messages_sent INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS tossed_message (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    graph_id TEXT NOT NULL UNIQUE,
    source TEXT NOT NULL,
    message_id TEXT NOT NULL,
    chat_id TEXT,
    uidl TEXT NOT NULL UNIQUE,
    tossed_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chat_map (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id TEXT NOT NULL UNIQUE,
    chat_b32 TEXT NOT NULL UNIQUE,
    reply_address TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL
);
