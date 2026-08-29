"""Simple CLI dashboard for routing telemetry."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from telemetry.logger import TelemetryLogger


def main() -> None:
    parser = argparse.ArgumentParser(description="View adaptive router telemetry")
    parser.add_argument(
        "--db",
        type=Path,
        default=Path("telemetry/routing.db"),
    )
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument(
        "--mode",
        choices=["recent", "summary"],
        default="recent",
    )
    args = parser.parse_args()

    logger = TelemetryLogger(args.db)
    if args.mode == "summary":
        print(json.dumps(logger.summary(), indent=2))
    else:
        print(json.dumps(logger.recent(args.limit), indent=2))


if __name__ == "__main__":
    main()
