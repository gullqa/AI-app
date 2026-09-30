"""小程序 API（/api/*）：微信登录 + 只读简报 + 限流问答 + 关注领域。"""
import httpx
from fastapi import APIRouter, Depends, Header, HTTPException

from . import auth, chat
from .config import Domain, env
from .store import UserStore


def make_router(domains: dict[str, Domain], store: UserStore) -> APIRouter:
    r = APIRouter(prefix="/api")

    def user(authorization: str | None = Header(None)) -> str:
        openid = auth.verify_token((authorization or "").removeprefix("Bearer "), env("INTEL_TOKEN_SECRET"))
        if not openid:
            raise HTTPException(401, "请重新登录")
        return openid

    def domain(key: str) -> Domain:
        if key not in domains:
            raise HTTPException(404, "unknown domain")
        return domains[key]

    @r.post("/login")
    def login(body: dict):
        secret = env("INTEL_TOKEN_SECRET")
        if not secret:
            raise HTTPException(500, "INTEL_TOKEN_SECRET not set")
        appid, wx_secret = env("WX_APPID"), env("WX_SECRET")
        if appid and wx_secret:
            d = httpx.get("https://api.weixin.qq.com/sns/jscode2session", timeout=10, params={
                "appid": appid, "secret": wx_secret, "js_code": body.get("code", ""),
                "grant_type": "authorization_code"}).json()
            if "openid" not in d:
                raise HTTPException(400, f"微信登录失败: {d.get('errmsg', d)}")
            openid = d["openid"]
        elif env("INTEL_DEV_LOGIN") == "1":
            openid = "dev-user"
        else:
            raise HTTPException(500, "WX_APPID/WX_SECRET not set")
        return {"token": auth.make_token(openid, secret)}

    @r.get("/domains")
    def list_domains(openid: str = Depends(user)):
        followed = set(store.follows(openid))
        return [{"key": k, "name": d.name, "followed": k in followed} for k, d in domains.items()]

    @r.put("/follow/{key}")
    def follow(key: str, body: dict, openid: str = Depends(user)):
        domain(key)
        store.set_follow(openid, key, bool(body.get("on")))
        return {"ok": True}

    @r.get("/briefing/{key}")
    def briefing(key: str, _: str = Depends(user)):
        domain(key)
        return {"briefing": store.last_briefing(key)}

    @r.post("/ask")
    def ask(body: dict, openid: str = Depends(user)):
        q = (body.get("q") or "").strip()
        key = body.get("domain", "")
        d = domain(key)
        if not q or len(q) > 300:
            raise HTTPException(400, "问题长度需在 1-300 字")
        if not store.take_quota(openid, int(env("INTEL_ASK_DAILY_LIMIT", "20"))):
            raise HTTPException(429, "今日提问次数已用完")
        return {"answer": chat.handle(f"{key} {q}", {key: d}, store)}

    return r
