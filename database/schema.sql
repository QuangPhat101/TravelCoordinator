PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS user_profile (
    user_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    email TEXT NOT NULL,
    avatar_path TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    last_login_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS eco_wallet (
    user_id TEXT PRIMARY KEY,
    total_eco_points INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES user_profile(user_id)
);

CREATE TABLE IF NOT EXISTS reward_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    points INTEGER NOT NULL,
    reason TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES user_profile(user_id)
);

CREATE TABLE IF NOT EXISTS crowd_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    zone TEXT NOT NULL,
    level INTEGER NOT NULL,
    recommendation TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_reward_transactions_user_id
ON reward_transactions(user_id);

CREATE INDEX IF NOT EXISTS idx_reward_transactions_created_at
ON reward_transactions(created_at);
