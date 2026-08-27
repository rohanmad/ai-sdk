#!/usr/bin/env python3
"""CLI demo for the adaptive inference router."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from packages.sdk.router import Router, RouterConfig  # noqa: E402
from packages.sdk.types import GenerateTextRequest  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Adaptive inference router demo")
    parser.add_argument("prompt", help="Prompt text to route and execute")
    parser.add_argument("--max-tokens", type=int, default=128)
    parser.add_argument("--policy", default="config/policy.yaml")
    args = parser.parse_args()

    router = Router.init(RouterConfig(policy_path=args.policy))
    response = router.generate_text(
        GenerateTextRequest(prompt=args.prompt, max_tokens=args.max_tokens)
    )
    print(json.dumps(response.to_dict(), indent=2))


if __name__ == "__main__":
    main()
