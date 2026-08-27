#!/usr/bin/env python3
"""Bridge for the TypeScript SDK — reads JSON from stdin, writes response to stdout."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from packages.sdk.router import Router, RouterConfig  # noqa: E402
from packages.sdk.types import GenerateTextRequest  # noqa: E402


def main() -> None:
    raw = json.load(sys.stdin)
    request_data = raw["request"]
    config_data = raw.get("config", {})

    router = Router.init(
        RouterConfig(
            policy_path=config_data.get("policyPath", "config/policy.yaml"),
            telemetry_db=config_data.get("telemetryDb", "telemetry/routing.db"),
            small_model_path=config_data.get("smallModelPath", ""),
            large_model_path=config_data.get("largeModelPath", ""),
            cloud_api_key=config_data.get("cloudApiKey"),
            cloud_model=config_data.get("cloudModel", "gpt-4o-mini"),
        )
    )

    response = router.generate_text(
        GenerateTextRequest(
            prompt=request_data["prompt"],
            model=request_data.get("model"),
            max_tokens=request_data.get("max_tokens", 256),
            temperature=request_data.get("temperature", 0.7),
            metadata=request_data.get("metadata", {}),
        )
    )
    print(json.dumps(response.to_dict()))


if __name__ == "__main__":
    main()
