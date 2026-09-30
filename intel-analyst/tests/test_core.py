import json

import pytest

from intel import chat
from intel.analyzer import briefing
from intel.channels import wecom
from intel.channels.feishu import _sign, parse_event
from intel.collectors import parse_feed, score
from intel.config import Domain
from intel.models import Item
from intel.store import Store

RSS = """<?xml version="1.0"?><rss version="2.0"><channel><title>t</title>
<item><title>TSMC expands CoWoS capacity</title><link>http://a/1</link>
<description>&lt;p&gt;HBM demand&lt;/p&gt;</description></item>
<item><title>Coupon giveaway wafer</title><link>http://a/2</link><description>x</description></item>
<item><title>Unrelated</title><link>http://a/3</link><description>cats</description></item>
</channel></rss>"""

D = Domain(key="carbon", name="半导体", sources=[], keywords={"CoWoS": 3, "HBM": 3, "wafer": 1},
           exclude=["giveaway"])


def test_parse_and_score(monkeypatch):
    items = parse_feed(RSS, "src", "carbon")
    assert len(items) == 3 and "<p>" not in items[0].summary
    s = [score(i, D) for i in items]
    assert s[0] > 5 and s[1] == -1 and s[2] == 0


def test_store_dedup():
    st = Store(":memory:")
    items = parse_feed(RSS, "src", "carbon")
    assert len(st.add_new(items)) == 3
    assert st.add_new(items) == []


@pytest.fixture(autouse=True)
def _no_llm_keys(monkeypatch):
    for k in ("ANTHROPIC_API_KEY", "DEEPSEEK_API_KEY", "WX_APPID", "WX_SECRET", "INTEL_DEV_LOGIN"):
        monkeypatch.delenv(k, raising=False)


def test_offline_briefing():
    it = Item("http://a/1", "TSMC CoWoS", "s", "src", "", "carbon", 5)
    assert "TSMC CoWoS" in briefing(D, [it])
    assert "没有发现" in briefing(D, [])


def test_chat_routing():
    st = Store(":memory:")
    st.add_new([Item("http://a/1", "TSMC CoWoS capacity", "s", "src", "", "carbon", 5)])
    ds = {"carbon": D}
    assert "carbon" in chat.handle("/域", ds, st)
    assert "未知领域" in chat.handle("/简报 nope", ds, st)
    assert "TSMC" in chat.handle("carbon CoWoS 产能", ds, st)


def test_feishu_parse_and_sign():
    payload = {"event": {"message": {"message_type": "text", "message_id": "m1",
               "content": json.dumps({"text": "@_user_1 semi HBM"}),
               "mentions": [{"key": "@_user_1"}]}}}
    assert parse_event(payload) == ("m1", "semi HBM")
    assert _sign("s", "1") == _sign("s", "1") and _sign("s", "1") != _sign("s", "2")


def test_wecom_chunks():
    parts = wecom._chunks("\n".join("行" * 100 for _ in range(50)))
    assert len(parts) > 1 and all(len(p) <= 1300 for p in parts)


def test_deepseek_call(monkeypatch):
    from intel import llm
    monkeypatch.setenv("DEEPSEEK_API_KEY", "k")
    assert llm.available()
    seen = {}

    class R:
        def raise_for_status(self): pass
        def json(self): return {"choices": [{"message": {"content": "答"}}]}

    def fake_post(url, **kw):
        seen.update(url=url, **kw)
        return R()

    monkeypatch.setattr(llm.httpx, "post", fake_post)
    assert llm.complete("sys", "usr") == "答"
    assert seen["url"] == "https://api.deepseek.com/chat/completions"
    assert seen["headers"]["Authorization"] == "Bearer k"
    assert seen["json"]["model"] == "deepseek-chat"
    assert seen["json"]["messages"][1]["content"] == "usr"


def test_token_roundtrip_and_tamper():
    from intel import auth
    t = auth.make_token("oX", "s")
    assert auth.verify_token(t, "s") == "oX"
    assert auth.verify_token(t, "other") is None
    assert auth.verify_token(t[:-2] + "xx", "s") is None
    assert auth.verify_token(auth.make_token("oX", "s", ttl=-1), "s") is None


def test_quota_and_follow():
    from intel.store import UserStore
    st = UserStore(":memory:")
    assert [st.take_quota("u", 2) for _ in range(3)] == [True, True, False]
    st.set_follow("u", "d", True)
    assert st.follows("u") == ["d"]


def test_api_flow(monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from intel.api import make_router
    from intel.store import UserStore
    monkeypatch.setenv("INTEL_TOKEN_SECRET", "s")
    monkeypatch.setenv("INTEL_ASK_DAILY_LIMIT", "1")
    st = UserStore(":memory:")
    st.add_new([Item("http://a/1", "carbon price CoWoS", "s", "src", "", "carbon", 5)])
    app = FastAPI()
    app.include_router(make_router({"carbon": D}, st))
    c = TestClient(app)
    assert c.get("/api/domains").status_code == 401
    assert c.post("/api/login", json={"code": "x"}).status_code == 500  # 未配置 WX、未开 dev 登录
    monkeypatch.setenv("INTEL_DEV_LOGIN", "1")
    h = {"Authorization": "Bearer " + c.post("/api/login", json={"code": "x"}).json()["token"]}
    assert c.get("/api/domains", headers=h).json()[0]["key"] == "carbon"
    ask = {"domain": "carbon", "q": "CoWoS"}
    assert c.post("/api/ask", json=ask, headers=h).status_code == 200
    assert c.post("/api/ask", json=ask, headers=h).status_code == 429
