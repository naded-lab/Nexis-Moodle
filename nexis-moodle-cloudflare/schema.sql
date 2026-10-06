CREATE TABLE IF NOT EXISTS users (
  telegram_id INTEGER PRIMARY KEY,
  moodle_username TEXT NOT NULL,
  password_encrypted TEXT NOT NULL,
  enabled INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS seen_items (
  telegram_id INTEGER NOT NULL,
  item_type TEXT NOT NULL,
  item_key TEXT NOT NULL,
  first_seen TEXT NOT NULL,
  PRIMARY KEY (telegram_id, item_type, item_key)
);
CREATE TABLE IF NOT EXISTS pending_logins (
  telegram_id INTEGER PRIMARY KEY,
  state TEXT NOT NULL,
  moodle_username TEXT,
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_users_enabled ON users(enabled);
CREATE INDEX IF NOT EXISTS idx_seen_items_user ON seen_items(telegram_id);
