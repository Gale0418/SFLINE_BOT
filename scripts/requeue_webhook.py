"""One-time operator recovery for an explicitly reviewed interrupted webhook."""
from __future__ import annotations

import argparse
from pathlib import Path

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
    requeue_interrupted(args.db, args.event_id)
    print(f"requeued interrupted event: {args.event_id}")


if __name__ == "__main__":
    main()
