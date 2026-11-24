"""Admin user creation and mail queuing without network access."""
from __future__ import annotations

import asyncio
from types import SimpleNamespace

from app.api.v1.admin import routes
from app.core.security import CurrentUser


class FakeTable:
    def __init__(self):
        self.inserted = []
        self.data = []

    def select(self, *_args): return self
    def limit(self, *_args): return self
    def eq(self, *_args): return self
    def order(self, *_args, **_kwargs): return self
    def insert(self, row):
        self.inserted.append(row)
        self.data = [{"id": "mail-1", **row, "status": "pending_provider"}]
        return self
    def execute(self): return SimpleNamespace(data=self.data)


class FakeClient:
    def __init__(self):
        self.outbox = FakeTable()
        self.created = []
        self.account = SimpleNamespace(id="new-user", email="new@example.com")
        self.auth = SimpleNamespace(admin=self)

    def table(self, name):
        assert name == "admin_email_outbox"
        return self.outbox

    def create_user(self, attributes):
        self.created.append(attributes)
        return SimpleNamespace(user=self.account)

    def get_user_by_id(self, _user_id):
        return SimpleNamespace(user=self.account)


def test_admin_creates_verified_or_unverified_account_and_queues_mail(monkeypatch):
    client = FakeClient()
    monkeypatch.setattr(routes, "get_service_client", lambda: client)
    admin = CurrentUser(id="admin-1", email="admin@example.com", token="test")

    for verified, kind in ((False, "verification"), (True, "account_verified")):
        result = asyncio.run(routes.create_user(
            routes.UserCreate(email="New@Example.com", full_name="New User", verified=verified), admin))
        assert result["email_status"] == "pending_provider"
        assert client.created[-1]["email_confirm"] is verified
        assert client.created[-1]["email"] == "new@example.com"
        assert "password" not in client.created[-1]
        assert client.outbox.inserted[-1]["email_type"] == kind
        assert client.outbox.inserted[-1]["created_by"] == admin.id


def test_custom_email_is_queued_not_reported_sent(monkeypatch):
    client = FakeClient()
    monkeypatch.setattr(routes, "get_service_client", lambda: client)
    admin = CurrentUser(id="admin-1", email="admin@example.com", token="test")

    result = asyncio.run(routes.queue_user_email(
        "new-user", routes.UserEmail(email_type="custom", subject="Hello", body="Message"), admin))
    assert result == {"id": "mail-1", "status": "pending_provider"}
    assert client.outbox.inserted[-1]["recipient_email"] == "new@example.com"
