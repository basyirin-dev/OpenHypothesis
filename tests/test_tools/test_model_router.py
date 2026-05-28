"""Tests for the model router and capability checker."""

import pytest

from openhypothesis.tools.model_router import CostRecord, GenerationResponse, ModelRouter


def test_model_router_init() -> None:
    router = ModelRouter()
    assert router is not None
    assert router._settings is not None


def test_cost_record_defaults() -> None:
    c = CostRecord()
    assert c.prompt_tokens == 0
    assert c.completion_tokens == 0
    assert c.total_tokens == 0
    assert c.cost_usd == 0.0
    assert c.model == ""


def test_cost_record_with_values() -> None:
    c = CostRecord(
        prompt_tokens=10,
        completion_tokens=20,
        total_tokens=30,
        cost_usd=0.001,
        model="gpt-4o",
    )
    assert c.prompt_tokens == 10
    assert c.total_tokens == 30
    assert c.cost_usd == 0.001


def test_generation_response_defaults() -> None:
    cost = CostRecord()
    r = GenerationResponse(content="hello", cost=cost, model_used="gpt-4o")
    assert r.content == "hello"
    assert r.finish_reason == ""


@pytest.mark.asyncio
async def test_capability_checker_known_model() -> None:
    from openhypothesis.tools.capability_checker import check_capabilities

    report = await check_capabilities("openai/gpt-4o")
    assert report.supports_tool_calling is True
    assert report.supports_json_mode is True
    assert report.max_context_length == 128000


@pytest.mark.asyncio
async def test_capability_checker_ollama() -> None:
    from openhypothesis.tools.capability_checker import check_capabilities

    report = await check_capabilities("ollama/llama3.1-8b")
    assert report.supports_tool_calling is True
    assert report.supports_json_mode is True
    assert report.provider == "ollama"
