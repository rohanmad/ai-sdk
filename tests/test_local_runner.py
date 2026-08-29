"""Tests for LocalRunner memory management."""

from __future__ import annotations

import gc
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from packages.execution.local_runner import LocalRunner, LocalRunnerConfig  # noqa: E402

SMALL = ROOT / "models/small/qwen2.5-1.5b-instruct-q4_k_m.gguf"


@pytest.mark.skipif(not SMALL.exists(), reason="GGUF model not downloaded")
def test_unload_clears_model_cache() -> None:
    runner = LocalRunner(
        LocalRunnerConfig(small_model_path=str(SMALL), n_ctx=512, n_threads=2)
    )
    runner.generate("hello", tier="small", max_tokens=4)
    assert "small" in runner._models

    runner.unload("small")
    assert "small" not in runner._models

    runner.unload()
    assert runner._models == {}
    gc.collect()
