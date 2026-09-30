import logging
import os
from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request

from . import chat
from .channels import feishu
from .config import env, load_domains
from .pipeline import run_domain
from .store import Store

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("intel")

domains = load_domains()
store = Store(env("INTEL_DB", "data/intel.db"))
scheduler = BackgroundScheduler()


@asynccontextmanager
async def lifespan(_: FastAPI):
    for d in domains.values():
        if d.schedule:
            scheduler.add_job(run_domain, CronTrigger.from_crontab(d.schedule), args=[d, store],
                              id=d.key, misfire_grace_time=3600, coalesce=True)
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(title="Intel Analyst", lifespan=lifespan)


def auth(token: str | None) -> None:
    expected = os.getenv("INTEL_API_TOKEN", "")
    if not expected or token != expected:
        raise HTTPException(401, "bad or missing X-Token (set INTEL_API_TOKEN)")


@app.get("/health")
def health():
    return {"ok": True, "domains": list(domains)}


@app.post("/run/{key}")
def run(key: str, send: bool = False, x_token: str | None = Header(None)):
    auth(x_token)
    if key not in domains:
        raise HTTPException(404, "unknown domain")
    return {"briefing": run_domain(domains[key], store, send=send)}


@app.get("/briefing/{key}")
def get_briefing(key: str, x_token: str | None = Header(None)):
    auth(x_token)
    return {"briefing": store.last_briefing(key)}


@app.post("/ask")
def ask(body: dict, x_token: str | None = Header(None)):
    auth(x_token)
    return {"answer": chat.handle(body.get("q", ""), domains, store)}


def _feishu_reply(message_id: str, text: str) -> None:
    try:
        feishu.reply_text(message_id, chat.handle(text, domains, store))
    except Exception:  # noqa: BLE001
        log.exception("feishu reply failed")


@app.post("/feishu/event")
async def feishu_event(req: Request, bg: BackgroundTasks):
    payload = await req.json()
    if "encrypt" in payload:
        raise HTTPException(400, "请在飞书后台关闭 Encrypt Key（本服务未实现加密事件）")
    if payload.get("type") == "url_verification":
        if payload.get("token") != env("FEISHU_VERIFICATION_TOKEN"):
            raise HTTPException(403, "bad token")
        return {"challenge": payload["challenge"]}
    if payload.get("header", {}).get("token") != env("FEISHU_VERIFICATION_TOKEN"):
        raise HTTPException(403, "bad token")
    if payload["header"].get("event_type") == "im.message.receive_v1":
        parsed = feishu.parse_event(payload)
        if parsed:
            bg.add_task(_feishu_reply, *parsed)  # 飞书要求 3 秒内响应，分析放后台
    return {"ok": True}
