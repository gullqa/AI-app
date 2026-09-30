"""聊天指令路由（飞书等对话渠道共用）。

  /域            列出领域
  /简报 <域>      最近一次简报
  /刷新 <域>      立即采集+分析（不推送）
  [<域>] <问题>   基于情报库问答；省略域时用第一个领域
"""
from .analyzer import answer
from .config import Domain
from .pipeline import run_domain
from .store import Store


def handle(text: str, domains: dict[str, Domain], store: Store) -> str:
    text = text.strip()
    if not text or text in ("/help", "帮助"):
        return __doc__ or ""
    if text in ("/域", "/domains"):
        return "\n".join(f"{k}: {d.name}" for k, d in domains.items())
    cmd, _, rest = text.partition(" ")
    if cmd in ("/简报", "/刷新"):
        key = rest.strip()
        if key not in domains:
            return f"未知领域 '{key}'，可选：{', '.join(domains)}"
        if cmd == "/刷新":
            return run_domain(domains[key], store, send=False)
        return store.last_briefing(key) or "还没有简报，先发送 /刷新 " + key
    key = cmd if cmd in domains else next(iter(domains))
    question = rest if cmd in domains else text
    d = domains[key]
    return answer(d, question, store.recent(key, days=14))
