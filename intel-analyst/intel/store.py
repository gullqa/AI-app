import sqlite3
from pathlib import Path

from .models import Item

SCHEMA = """
CREATE TABLE IF NOT EXISTS items(
  id TEXT PRIMARY KEY, domain TEXT, url TEXT, title TEXT, summary TEXT,
  source TEXT, published TEXT, score REAL, fetched_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE INDEX IF NOT EXISTS idx_items_domain ON items(domain, fetched_at);
CREATE TABLE IF NOT EXISTS briefings(
  id INTEGER PRIMARY KEY AUTOINCREMENT, domain TEXT, body TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP);
"""


class Store:
    def __init__(self, path: str):
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)

    def add_new(self, items: list[Item]) -> list[Item]:
        """写入并返回此前未见过的条目（去重）。"""
        new = []
        for it in items:
            cur = self.db.execute(
                "INSERT OR IGNORE INTO items(id,domain,url,title,summary,source,published,score)"
                " VALUES(?,?,?,?,?,?,?,?)",
                (it.id, it.domain, it.url, it.title, it.summary, it.source, it.published, it.score),
            )
            if cur.rowcount:
                new.append(it)
        self.db.commit()
        return new

    def recent(self, domain: str, days: int = 7, limit: int = 200) -> list[Item]:
        rows = self.db.execute(
            "SELECT * FROM items WHERE domain=? AND fetched_at >= datetime('now', ?)"
            " ORDER BY score DESC, fetched_at DESC LIMIT ?",
            (domain, f"-{days} days", limit),
        ).fetchall()
        return [Item(r["url"], r["title"], r["summary"], r["source"], r["published"], r["domain"], r["score"]) for r in rows]

    def save_briefing(self, domain: str, body: str) -> None:
        self.db.execute("INSERT INTO briefings(domain, body) VALUES(?,?)", (domain, body))
        self.db.commit()

    def last_briefing(self, domain: str) -> str | None:
        r = self.db.execute(
            "SELECT body FROM briefings WHERE domain=? ORDER BY id DESC LIMIT 1", (domain,)
        ).fetchone()
        return r["body"] if r else None
