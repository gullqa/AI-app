import logging

from . import feishu, wecom

log = logging.getLogger("intel")


def push(channels: list[str], title: str, body: str) -> dict[str, str]:
    """向各渠道推送；一个渠道失败不影响其它。返回每个渠道的结果。"""
    senders = {"feishu": feishu.send_webhook, "wecom": wecom.send_webhook}
    result = {}
    for ch in channels:
        try:
            result[ch] = senders[ch](title, body)
        except Exception as ex:  # noqa: BLE001
            log.error("push to %s failed: %s", ch, ex)
            result[ch] = f"error: {ex}"
    return result
