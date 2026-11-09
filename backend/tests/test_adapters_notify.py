import json

import httpx

from csx.adapters.notify import (
    FeishuNotifier,
    NotificationDispatcher,
    TelegramNotifier,
    WebhookNotifier,
)


def make_client(requests):
    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={"ok": True, "code": 0})

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_webhook_posts_event_and_payload():
    requests = []
    sender = WebhookNotifier(make_client(requests))
    sender.send("transfer_success", {"title": "电影"}, {"url": "https://notify.test/hook"})
    assert requests[0].url.path == "/hook"
    body = json.loads(requests[0].read())
    assert body["event"] == "transfer_success"
    assert body["data"] == {"title": "电影"}
    assert body["text"] == ""


def test_telegram_markdown_payload():
    requests = []
    sender = TelegramNotifier(make_client(requests))
    sender.send("task_dead_letter", {"task_id": 7}, {"token": "token", "chat_id": "room"})
    assert requests[0].url.path == "/bottoken/sendMessage"
    body = json.loads(requests[0].read())
    assert "parse_mode" not in body
    assert body["text"] == "task_dead_letter\ntask_id: 7"


def test_feishu_uses_interactive_rich_card():
    requests = []
    sender = FeishuNotifier(make_client(requests))
    sender.send("checkin_report", {"account": "115"}, {"webhook_url": "https://notify.test/bot"})
    assert b'"msg_type":"interactive"' in requests[0].read()


def test_dispatcher_fans_out_and_contains_transport_errors():
    class Sender:
        def __init__(self, should_fail=False):
            self.should_fail = should_fail

        def send(self, event, payload, config):
            if self.should_fail:
                raise httpx.ConnectError("offline")

    dispatcher = NotificationDispatcher({"webhook": Sender(), "telegram": Sender(should_fail=True)})
    result = dispatcher.dispatch(
        {
            "webhook": {"enabled": True},
            "telegram": {"enabled": True},
            "feishu": {"enabled": False},
        },
        "upgrade_success",
        {"title": "test"},
    )
    assert result["webhook"] == "sent"
    assert result["telegram"].startswith("failed: offline")
