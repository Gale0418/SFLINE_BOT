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
    serve(app, host="127.0.0.1", port=settings.app_port, threads=4)


if __name__ == "__main__":
    main()
