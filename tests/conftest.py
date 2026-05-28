"""Shared fixtures for the OpenHypothesis test suite."""

import asyncio
from collections.abc import AsyncGenerator

import pytest


@pytest.fixture(scope="session")
def event_loop() -> AsyncGenerator[asyncio.AbstractEventLoop, None]:
    """Create a single event loop for the entire test session.

    Required by ``pytest-asyncio`` when using ``asyncio_mode = auto``.
    """
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
