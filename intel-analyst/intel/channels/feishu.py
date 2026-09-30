"""飞书：群自定义机器人 webhook 推送 + 自建应用事件回调（对话问答）。"""
import base64
import hashlib
import hmac
import json
import time

import httpx

from ..config import env

API = "https://open.feishu.cn/open-apis"


def _sign(secret: str, ts: str) -> str:
    key = f"{ts}\n{secret}".encode()
    return base64.b64encode(hmac.new(key, b"", hashlib.sha256).digest()).decode()


def send_webhook(title: str, body: str) -> str:
    url = env("FEISHU_WEBHOOK")
    if not url:
        return "skipped: FEISHU_WEBHOOK not set"
    payload: dict = {
        "msg_type": "interactive",
        "card": {
            "header": {"title": {"tag": "plain_text", "content": title}, "template": "blue"},
            "elements": [{"tag": "markdown", "content": body[:28000]}],
        },
    }
    if secret := env("FEISHU_WEBHOOK_SECRET"):
        ts = str(int(time.time()))
        payload.update(timestamp=ts, sign=_sign(secret, ts))
    r = httpx.post(url, json=payload, timeout=15)
    data = r.json()
    if data.get("code", 0) != 0:
        raise RuntimeError(data)
    return "ok"


_token = {"v": "", "exp": 0.0}


def tenant_token() -> str:
    if _token["exp"] > time.time() + 60:
        return _token["v"]
    r = httpx.post(f"{API}/auth/v3/tenant_access_token/internal", timeout=15,
                   json={"app_id": env("FEISHU_APP_ID"), "app_secret": env("FEISHU_APP_SECRET")})
    d = r.json()
    if d.get("code") != 0:
        raise RuntimeError(d)
    _token.update(v=d["tenant_access_token"], exp=time.time() + d["expire"])
    return _token["v"]


def reply_text(message_id: str, text: str) -> None:
    httpx.post(f"{API}/im/v1/messages/{message_id}/reply", timeout=15,
               headers={"Authorization": f"Bearer {tenant_token()}"},
               json={"msg_type": "text", "content": json.dumps({"text": text})})


def parse_event(payload: dict) -> tuple[str, str] | None:
    """从 im.message.receive_v1 事件取 (message_id, 纯文本)；非文本消息返回 None。"""
    ev = payload.get("event", {})
    msg = ev.get("message", {})
    if msg.get("message_type") != "text":
        return None
    text = json.loads(msg["content"]).get("text", "")
    for m in msg.get("mentions", []) or []:  # 去掉 @_user_1 之类的占位
        text = text.replace(m.get("key", ""), "")
    return msg["message_id"], text.strip()
