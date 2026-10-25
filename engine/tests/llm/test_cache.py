"""Disk cache keying and get/set."""

from __future__ import annotations

from pathlib import Path

from takeoff_engine.llm.cache import DiskCache, cache_key


def test_cache_key_stable_and_sensitive_to_inputs() -> None:
    a = cache_key("m", "legend_v1", text_parts=["hello"], image_parts=[b"img"])
    b = cache_key("m", "legend_v1", text_parts=["hello"], image_parts=[b"img"])
    c = cache_key("m", "legend_v1", text_parts=["hello!"], image_parts=[b"img"])
    d = cache_key("m", "legend_v1", text_parts=["hello"], image_parts=[b"img2"])
    e = cache_key("other", "legend_v1", text_parts=["hello"], image_parts=[b"img"])
    assert a == b
    assert a != c
    assert a != d
    assert a != e
    assert len(a) == 64


def test_disk_cache_roundtrip(tmp_path: Path) -> None:
    cache = DiskCache(tmp_path)
    key = cache_key("m", "v1", text_parts=["x"])
    assert cache.get(key) is None
    cache.set(key, {"ok": True, "n": 1})
    assert cache.get(key) == {"ok": True, "n": 1}
