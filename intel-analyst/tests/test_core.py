import json

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


def test_offline_briefing(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    it = Item("http://a/1", "TSMC CoWoS", "s", "src", "", "carbon", 5)
    assert "TSMC CoWoS" in briefing(D, [it])
    assert "没有发现" in briefing(D, [])


def test_chat_routing(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    st = Store(":memory:")
    st.add_new([Item("http://a/1", "TSMC CoWoS capacity", "s", "src", "", "carbon", 5)])
    ds = {"carbon": D}
    assert "carbon" in chat.handle("/域", ds, st)
    assert "未知领域" in chat.handle("/简报 nope", ds, st)
    assert "TSMC" in chat.handle("semi CoWoS 产能", ds, st)


def test_feishu_parse_and_sign():
    payload = {"event": {"message": {"message_type": "text", "message_id": "m1",
               "content": json.dumps({"text": "@_user_1 semi HBM"}),
               "mentions": [{"key": "@_user_1"}]}}}
    assert parse_event(payload) == ("m1", "semi HBM")
    assert _sign("s", "1") == _sign("s", "1") and _sign("s", "1") != _sign("s", "2")


def test_wecom_chunks():
    parts = wecom._chunks("\n".join("行" * 100 for _ in range(50)))
    assert len(parts) > 1 and all(len(p) <= 1300 for p in parts)
