import types

import pytest


@pytest.fixture(autouse=True)
def reset_dedup_state():
    """Clear print-job de-dup state between tests so they don't leak into
    each other via the module-level sets/deque in client.__init__."""
    import client

    client._inflight_jobs.clear()
    client._recent_jobs.clear()
    client._recent_jobs_set.clear()
    yield
    client._inflight_jobs.clear()
    client._recent_jobs.clear()
    client._recent_jobs_set.clear()


@pytest.fixture
def mock_label():
    """Factory for fake brother_ql ALL_LABELS entries."""

    def _make(identifier: str, dots_printable: tuple[int, int]):
        return types.SimpleNamespace(identifier=identifier, dots_printable=dots_printable)

    return _make


@pytest.fixture
def tmp_env_file(tmp_path):
    """A minimal .env file path for persist_token_to_env tests."""
    path = tmp_path / ".env"
    path.write_text("BACKEND_URL=http://localhost:8000\n")
    return path
