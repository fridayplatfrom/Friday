import pytest


@pytest.fixture(autouse=True)
def isolated_state(tmp_path, monkeypatch):
    """Never read or write a developer's source imports or conversation memory."""
    monkeypatch.setenv("TINY_EXPERT_STATE_DIR", str(tmp_path / "state"))
