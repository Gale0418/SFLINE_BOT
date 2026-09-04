from __future__ import annotations

from waitress import serve

from .app import create_app
from .config import ConfigurationError, Settings


def main() -> None:
    try:
        settings = Settings.from_env()
    except ConfigurationError as exc:
        raise SystemExit(str(exc)) from exc
    app = create_app(settings)
    dispatcher = app.extensions.get("event_dispatcher")
    try:
        serve(app, host="127.0.0.1", port=settings.app_port, threads=4)
    finally:
        if dispatcher is not None:
            dispatcher.shutdown(wait=True)


if __name__ == "__main__":
    main()
