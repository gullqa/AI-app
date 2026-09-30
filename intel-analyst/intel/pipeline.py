import logging

from .analyzer import briefing
from .channels import push
from .collectors import collect
from .config import Domain
from .store import Store

log = logging.getLogger("intel")


def run_domain(d: Domain, store: Store, send: bool = True) -> str:
    items, errors = collect(d)
    new = store.add_new(items)
    log.info("%s: %d relevant, %d new, %d source errors", d.key, len(items), len(new), len(errors))
    for e in errors:
        log.warning("source error: %s", e)
    body = briefing(d, new)
    if errors:
        body += "\n\n> ⚠️ 部分数据源抓取失败：" + "；".join(errors)
    store.save_briefing(d.key, body)
    if send:
        push(d.channels, f"{d.name}情报简报", body)
    return body
