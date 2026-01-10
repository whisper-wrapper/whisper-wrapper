from src import config


def test_is_wayland_from_session_type(monkeypatch):
    monkeypatch.setenv("XDG_SESSION_TYPE", "wayland")
    assert config.is_wayland() is True


def test_get_display_server_prefers_session_type(monkeypatch):
    monkeypatch.setenv("XDG_SESSION_TYPE", "x11")
    assert config.get_display_server() == "x11"


def test_get_display_server_fallbacks(monkeypatch):
    monkeypatch.delenv("XDG_SESSION_TYPE", raising=False)

    monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
    monkeypatch.delenv("DISPLAY", raising=False)
    assert config.get_display_server() == "wayland"

    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    monkeypatch.setenv("DISPLAY", ":0")
    assert config.get_display_server() == "x11"

    monkeypatch.delenv("DISPLAY", raising=False)
    assert config.get_display_server() == "unknown"
