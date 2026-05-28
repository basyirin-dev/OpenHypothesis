"""Smoke test that the public API can be imported."""

from openhypothesis import Discover


def test_import() -> None:
    assert Discover is not None
