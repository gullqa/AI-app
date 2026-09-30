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


class UserStore(Store):
    """在 Store 基础上增加小程序用户：关注领域与每日问答配额。"""

    def __init__(self, path: str):
        super().__init__(path)
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS follows(openid TEXT, domain TEXT, PRIMARY KEY(openid, domain));
        CREATE TABLE IF NOT EXISTS usage(openid TEXT, day TEXT, n INTEGER DEFAULT 0, PRIMARY KEY(openid, day));
        """)

    def follows(self, openid: str) -> list[str]:
        return [r[0] for r in self.db.execute("SELECT domain FROM follows WHERE openid=?", (openid,))]

    def set_follow(self, openid: str, domain: str, on: bool) -> None:
        if on:
            self.db.execute("INSERT OR IGNORE INTO follows VALUES(?,?)", (openid, domain))
        else:
            self.db.execute("DELETE FROM follows WHERE openid=? AND domain=?", (openid, domain))
        self.db.commit()

    def take_quota(self, openid: str, limit: int) -> bool:
        """原子地消耗一次配额；超限返回 False。"""
        self.db.execute("INSERT OR IGNORE INTO usage(openid, day, n) VALUES(?, date('now'), 0)", (openid,))
        cur = self.db.execute(
            "UPDATE usage SET n=n+1 WHERE openid=? AND day=date('now') AND n<?", (openid, limit))
        self.db.commit()
        return cur.rowcount == 1
