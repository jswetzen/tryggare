import requests

import client


def _mock_session(monkeypatch, *, csrf_tokens, post_responses):
    """Patch client.requests.Session() to return a fake session.

    csrf_tokens: values returned by session.cookies.get('csrftoken') in order
    post_responses: responses returned by session.post(...) in order
    """
    csrf_iter = iter(csrf_tokens)
    post_iter = iter(post_responses)

    class FakeCookies:
        def get(self, name):
            return next(csrf_iter)

    class FakeSession:
        def __init__(self):
            self.cookies = FakeCookies()

        def get(self, url, timeout=None):
            resp = requests.Response()
            resp.status_code = 200
            return resp

        def post(self, url, json=None, headers=None, timeout=None):
            return next(post_iter)

    monkeypatch.setattr(client.requests, "Session", lambda: FakeSession())


def _fake_response(status_code=200, json_data=None):
    resp = requests.Response()
    resp.status_code = status_code
    if json_data is not None:
        import json as json_module

        resp._content = json_module.dumps(json_data).encode()
    return resp


def test_bootstrap_token_happy_path(monkeypatch):
    login_resp = _fake_response(200)
    provision_resp = _fake_response(200, {"token": "abc123"})
    _mock_session(
        monkeypatch,
        csrf_tokens=["csrf1", "csrf2"],
        post_responses=[login_resp, provision_resp],
    )

    token = client.bootstrap_token("staffuser", "staffpass")
    assert token == "abc123"


def test_bootstrap_token_propagates_http_error(monkeypatch):
    login_resp = _fake_response(401)
    _mock_session(
        monkeypatch,
        csrf_tokens=["csrf1"],
        post_responses=[login_resp],
    )

    try:
        client.bootstrap_token("staffuser", "wrongpass")
        assert False, "expected HTTPError"
    except requests.exceptions.HTTPError:
        pass


def test_persist_token_to_env_creates_new_file(monkeypatch, tmp_env_file):
    monkeypatch.setattr(client, "DOTENV_PATH", str(tmp_env_file))
    client.persist_token_to_env("newtoken")
    content = tmp_env_file.read_text()
    assert "PRINTER_TOKEN=newtoken" in content


def test_persist_token_to_env_replaces_existing_line(monkeypatch, tmp_path):
    path = tmp_path / ".env"
    path.write_text("BACKEND_URL=http://x\nPRINTER_TOKEN=oldtoken\n")
    monkeypatch.setattr(client, "DOTENV_PATH", str(path))

    client.persist_token_to_env("newtoken")

    content = path.read_text()
    assert "PRINTER_TOKEN=newtoken" in content
    assert "PRINTER_TOKEN=oldtoken" not in content


def test_persist_token_to_env_strips_staff_credentials(monkeypatch, tmp_path):
    path = tmp_path / ".env"
    path.write_text("STAFF_USERNAME=admin\nSTAFF_PASSWORD=secret\n")
    monkeypatch.setattr(client, "DOTENV_PATH", str(path))

    client.persist_token_to_env("newtoken")

    content = path.read_text()
    assert "STAFF_USERNAME" not in content
    assert "STAFF_PASSWORD" not in content
    assert "PRINTER_TOKEN=newtoken" in content


def test_persist_token_to_env_oserror_warns_not_raises(monkeypatch, tmp_path, caplog):
    import logging

    caplog.set_level(logging.WARNING, logger="printer-client")

    # A directory that doesn't exist as a parent makes write_text raise OSError.
    bogus_path = tmp_path / "nonexistent-dir" / ".env"
    monkeypatch.setattr(client, "DOTENV_PATH", str(bogus_path))

    client.persist_token_to_env("newtoken")  # should not raise

    assert any("Could not write token" in r.message for r in caplog.records)


def test_ensure_token_skips_provisioning_when_token_set(monkeypatch):
    monkeypatch.setattr(client, "PRINTER_TOKEN", "existing-token")

    def _boom(*args, **kwargs):
        raise AssertionError("bootstrap_token should not be called")

    monkeypatch.setattr(client, "bootstrap_token", _boom)
    client.ensure_token(non_interactive=True)


def test_ensure_token_provisions_and_persists_when_blank(monkeypatch):
    monkeypatch.setattr(client, "PRINTER_TOKEN", "")
    monkeypatch.setattr(
        client, "_resolve_credentials", lambda non_interactive: ("u", "p")
    )
    monkeypatch.setattr(client, "bootstrap_token", lambda u, p: "fresh-token")

    persisted = {}
    monkeypatch.setattr(
        client, "persist_token_to_env", lambda token: persisted.setdefault("token", token)
    )

    client.ensure_token(non_interactive=True)

    assert client.PRINTER_TOKEN == "fresh-token"
    assert persisted["token"] == "fresh-token"


def test_resolve_credentials_returns_env_vars_when_both_set(monkeypatch):
    monkeypatch.setattr(client, "STAFF_USERNAME", "envuser")
    monkeypatch.setattr(client, "STAFF_PASSWORD", "envpass")

    username, password = client._resolve_credentials(non_interactive=False)
    assert (username, password) == ("envuser", "envpass")


def test_resolve_credentials_raises_in_non_interactive_with_no_creds(monkeypatch):
    monkeypatch.setattr(client, "STAFF_USERNAME", "")
    monkeypatch.setattr(client, "STAFF_PASSWORD", "")

    try:
        client._resolve_credentials(non_interactive=True)
        assert False, "expected RuntimeError"
    except RuntimeError:
        pass


def test_reprovision_after_rejection_returns_true_with_staff_creds(monkeypatch):
    monkeypatch.setattr(client, "STAFF_USERNAME", "u")
    monkeypatch.setattr(client, "STAFF_PASSWORD", "p")
    monkeypatch.setattr(client, "bootstrap_token", lambda u, p: "new-token")
    monkeypatch.setattr(client, "persist_token_to_env", lambda token: None)

    assert client._reprovision_after_rejection() is True
    assert client.PRINTER_TOKEN == "new-token"


def test_reprovision_after_rejection_returns_false_without_creds(monkeypatch):
    monkeypatch.setattr(client, "STAFF_USERNAME", "")
    monkeypatch.setattr(client, "STAFF_PASSWORD", "")

    assert client._reprovision_after_rejection() is False
