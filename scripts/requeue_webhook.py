"""One-time operator recovery for an explicitly reviewed interrupted webhook."""
from __future__ import annotations

import argparse
from pathlib import Path

from eternal_polaris.app import _event_key
from eternal_polaris.config import Settings
from eternal_polaris.dispatcher import requeue_interrupted


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--event-id", required=True)
    parser.add_argument("--confirm-event-id", required=True)
    parser.add_argument("--accept-duplicate-reply-risk", action="store_true")
    args = parser.parse_args()
    if args.event_id != args.confirm_event_id:
        raise SystemExit("event ID confirmation does not match")
    if not args.accept_duplicate_reply_risk:
        raise SystemExit("explicit --accept-duplicate-reply-risk is required")
    settings = Settings.from_env()
    try:
        requeue_interrupted(
            args.db,
            args.event_id,
            max_persisted_jobs=(
                settings.webhook_worker_threads + settings.webhook_queue_capacity
            ),
            max_persisted_per_key=settings.webhook_max_pending_per_key + 1,
            key_fn=lambda event: _event_key(event, settings.line_channel_secret),
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    print(f"requeued interrupted event: {args.event_id}")


if __name__ == "__main__":
    main()
