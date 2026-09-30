"""企业微信群机器人 webhook 推送（微信生态中官方支持、最稳定的推送方式）。"""
import httpx

from ..config import env



def _chunks(text: str, n: int = 1200) -> list[str]:
    out, cur = [], ""
    for para in text.split("\n"):
        if len(cur) + len(para) + 1 > n and cur:
            out.append(cur)
            cur = ""
        cur += para + "\n"
    return out + ([cur] if cur.strip() else [])


def send_webhook(title: str, body: str) -> str:
    url = env("WECOM_WEBHOOK")
    if not url:
        return "skipped: WECOM_WEBHOOK not set"
    for i, part in enumerate(_chunks(f"**{title}**\n{body}")):
        r = httpx.post(url, json={"msgtype": "markdown", "markdown": {"content": part}}, timeout=15)
        d = r.json()
        if d.get("errcode", 0) != 0:
            raise RuntimeError(d)
    return "ok"
