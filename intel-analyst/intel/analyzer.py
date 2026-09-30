from . import llm
from .config import Domain
from .models import Item

SYSTEM = """你是{role}。请基于给定情报条目撰写专业简报，要求：
1. 只使用条目中的信息，不编造；每个结论用 [编号] 标注来源，条目不足以支持时明确说"证据不足"。
2. 严格区分「事实」与「你的判断」，判断需给出置信度（高/中/低）与理由。
3. 按分析框架逐项展开：{framework}。
4. 输出中文 Markdown，结构：## 一句话结论 / ## 关键信号（3-5条） / ## 分框架分析 / ## 风险与不确定性 / ## 后续应跟踪的指标。
5. 简洁，去除营销话术与重复报道。"""


def format_items(items: list[Item]) -> str:
    return "\n".join(
        f"[{i}] ({it.source}, {it.published or '日期未知'}) {it.title}\n    {it.summary[:400]}\n    {it.url}"
        for i, it in enumerate(items, 1)
    )


def offline_digest(d: Domain, items: list[Item]) -> str:
    lines = [f"## {d.name}情报速览（离线模式：未配置模型 API Key，仅按关键词排序）"]
    lines += [f"{i}. **{it.title}**（{it.source}，相关度 {it.score:g}）\n   {it.url}" for i, it in enumerate(items, 1)]
    return "\n".join(lines)


def briefing(d: Domain, items: list[Item], top: int = 25) -> str:
    items = sorted(items, key=lambda i: -i.score)[:top]
    if not items:
        return f"## {d.name}\n本周期没有发现相关新情报。"
    if not llm.available():
        return offline_digest(d, items)
    body = llm.complete(SYSTEM.format(role=d.analyst_role, framework="、".join(d.framework) or "自行判断"),
                f"领域：{d.name}\n情报条目：\n{format_items(items)}")
    refs = "\n".join(f"[{i}] {it.title} — {it.url}" for i, it in enumerate(items, 1))
    return f"# {d.name}情报简报\n\n{body}\n\n---\n**来源**\n{refs}"


def answer(d: Domain, question: str, pool: list[Item], top: int = 12) -> str:
    """基于已入库情报回答问题（简单关键词检索 + LLM）。"""
    terms = [t for t in question.lower().replace("，", " ").replace("？", " ").split() if len(t) > 1]

    def rel(it: Item) -> float:
        t = f"{it.title} {it.summary}".lower()
        return sum(t.count(x) for x in terms) + 0.1 * it.score

    hits = sorted(pool, key=rel, reverse=True)[:top]
    if not hits:
        return "情报库里暂时没有相关内容。"
    if not llm.available():
        return offline_digest(d, hits)
    return llm.complete(
        f"你是{d.analyst_role}。只依据给定情报回答，用 [编号] 引用，证据不足就直说，并区分事实与判断。中文，简洁。",
        f"问题：{question}\n\n情报：\n{format_items(hits)}", 1200)
