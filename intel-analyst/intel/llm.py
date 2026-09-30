"""模型层：DeepSeek（默认，OpenAI 兼容接口，境内可直连）或 Anthropic，用 INTEL_LLM_PROVIDER 切换。"""
import httpx

from .config import env


def provider() -> str:
    return env("INTEL_LLM_PROVIDER", "deepseek").lower()


def available() -> bool:
    return bool(env("DEEPSEEK_API_KEY") if provider() == "deepseek" else env("ANTHROPIC_API_KEY"))


def complete(system: str, user: str, max_tokens: int = 2500) -> str:
    if provider() == "deepseek":
        base = env("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
        r = httpx.post(
            f"{base}/chat/completions", timeout=180,
            headers={"Authorization": f"Bearer {env('DEEPSEEK_API_KEY')}"},
            json={"model": env("INTEL_MODEL", "deepseek-chat"), "max_tokens": max_tokens, "temperature": 0.3,
                  "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]},
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    import anthropic
    msg = anthropic.Anthropic().messages.create(
        model=env("INTEL_MODEL", "claude-sonnet-5-5"), max_tokens=max_tokens,
        system=system, messages=[{"role": "user", "content": user}])
    return "".join(b.text for b in msg.content if b.type == "text")
