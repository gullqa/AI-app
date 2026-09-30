"""无第三方依赖的 HMAC 签名令牌（小程序登录后使用）。"""
import base64
import hashlib
import hmac
import time


def _sig(secret: str, payload: str) -> str:
    return base64.urlsafe_b64encode(hmac.new(secret.encode(), payload.encode(), hashlib.sha256).digest()).decode()


def make_token(openid: str, secret: str, ttl: int = 30 * 86400) -> str:
    payload = f"{openid}.{int(time.time()) + ttl}"
    return f"{payload}.{_sig(secret, payload)}"


def verify_token(token: str, secret: str) -> str | None:
    try:
        openid, exp, sig = token.rsplit(".", 2)
    except ValueError:
        return None
    if not secret or not hmac.compare_digest(sig, _sig(secret, f"{openid}.{exp}")):
        return None
    return openid if int(exp) > time.time() else None
