from __future__ import annotations

import pytest

import eternal_polaris.__main__ as main_module
from eternal_polaris.config import ConfigurationError


class FakeDispatcher:
    def __init__(self):
        self.shutdown_calls = []

    def shutdown(self, *, wait=True):
        self.shutdown_calls.append(wait)


def test_main_serves_and_shuts_down_dispatcher(monkeypatch, settings):
    dispatcher = FakeDispatcher()
    app = type("App", (), {"extensions": {"event_dispatcher": dispatcher}})()
    captured = {}

    monkeypatch.setattr(
        main_module.Settings,
        "from_env",
        classmethod(lambda cls: settings),
    )
    monkeypatch.setattr(main_module, "create_app", lambda received: app)

    def fake_serve(received_app, **kwargs):
        captured["app"] = received_app
        captured["kwargs"] = kwargs

    monkeypatch.setattr(main_module, "serve", fake_serve)
    main_module.main()

    assert captured["app"] is app
    assert captured["kwargs"] == {
        "host": "127.0.0.1",
        "port": settings.app_port,
        "threads": 4,
    }
    assert dispatcher.shutdown_calls == [True]


def test_main_shuts_down_even_when_server_raises(monkeypatch, settings):
    dispatcher = FakeDispatcher()
    app = type("App", (), {"extensions": {"event_dispatcher": dispatcher}})()
    monkeypatch.setattr(
        main_module.Settings,
        "from_env",
        classmethod(lambda cls: settings),
    )
    monkeypatch.setattr(main_module, "create_app", lambda received: app)
    monkeypatch.setattr(
        main_module,
        "serve",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("server stopped")),
    )

    with pytest.raises(RuntimeError, match="server stopped"):
        main_module.main()
    assert dispatcher.shutdown_calls == [True]


def test_main_reports_safe_configuration_error(monkeypatch):
    def fail(cls):
        raise ConfigurationError("缺少必要設定：OPENAI_API_KEY")

    monkeypatch.setattr(main_module.Settings, "from_env", classmethod(fail))
    with pytest.raises(SystemExit, match="OPENAI_API_KEY"):
        main_module.main()
