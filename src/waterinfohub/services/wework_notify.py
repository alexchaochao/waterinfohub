import os
import requests


def send_wework_message(content: str, webhook_url: str = None):
    """Send a text message to Enterprise WeChat webhook.

    :param content: message text
    :param webhook_url: webhook URL; if None, read from WEWORK_WEBHOOK_URL
    :return: True on success, False on failure
    """
    if webhook_url is None:
        webhook_url = os.getenv("WEWORK_WEBHOOK_URL")
    if not webhook_url:
        raise ValueError("WEWORK_WEBHOOK_URL not configured")
    data = {"msgtype": "text", "text": {"content": content}}
    try:
        resp = requests.post(webhook_url, json=data, timeout=5)
        resp.raise_for_status()
        return True
    except Exception as e:
        print(f"[WeWork Notify] send failed: {e}")
        return False
