import time
from collections.abc import AsyncGenerator, Sequence
from typing import Any

from litellm import acompletion, completion, completion_cost
from pydantic import BaseModel

from openhypothesis.config.schema import RouterConfig
from openhypothesis.config.settings import Settings


class CostRecord(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    model: str = ""


class GenerationResponse(BaseModel):
    content: str
    cost: CostRecord
    model_used: str
    finish_reason: str = ""


class ModelRouter:
    def __init__(
        self,
        settings: Settings | None = None,
        router_config: RouterConfig | None = None,
    ) -> None:
        self._settings = settings or Settings()
        cfg = router_config or self._settings.app_config.router
        import litellm as _litellm

        _litellm.request_timeout = cfg.request_timeout  # type: ignore[attr-defined]
        _litellm.num_retries_on_timeout = cfg.num_retries_on_timeout

    @staticmethod
    def _extract_cost(response: Any) -> CostRecord:
        usage = getattr(response, "usage", None)
        if usage is None:
            return CostRecord(model=getattr(response, "model", ""))
        try:
            cost = completion_cost(completion_response=response)
        except Exception:
            cost = 0.0
        return CostRecord(
            prompt_tokens=getattr(usage, "prompt_tokens", 0),
            completion_tokens=getattr(usage, "completion_tokens", 0),
            total_tokens=getattr(usage, "total_tokens", 0),
            cost_usd=float(cost),
            model=getattr(response, "model", ""),
        )

    def generate(
        self,
        model: str,
        messages: Sequence[dict[str, Any]],
        **kwargs: Any,
    ) -> GenerationResponse:
        response = completion(model=model, messages=messages, **kwargs)
        choice = response.choices[0]
        return GenerationResponse(
            content=choice.message.content or "",
            cost=self._extract_cost(response),
            model_used=getattr(response, "model", model),
            finish_reason=choice.finish_reason or "",
        )

    async def agenerate(
        self,
        model: str,
        messages: Sequence[dict[str, Any]],
        **kwargs: Any,
    ) -> GenerationResponse:
        response = await acompletion(model=model, messages=messages, **kwargs)
        choice = response.choices[0]
        return GenerationResponse(
            content=choice.message.content or "",
            cost=self._extract_cost(response),
            model_used=getattr(response, "model", model),
            finish_reason=choice.finish_reason or "",
        )

    async def astream(
        self,
        model: str,
        messages: Sequence[dict[str, Any]],
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        response = await acompletion(model=model, messages=messages, stream=True, **kwargs)
        async for chunk in response:
            delta = chunk.choices[0].delta
            content = getattr(delta, "content", None)
            if content:
                yield content

    def generate_with_fallbacks(
        self,
        primary_model: str,
        messages: Sequence[dict[str, Any]],
        fallbacks: list[str] | None = None,
        **kwargs: Any,
    ) -> GenerationResponse:
        models_to_try = [primary_model] + (fallbacks or [])
        rate_limited: set[str] = set()
        expirations: dict[str, float] = {}
        start = time.time()

        while time.time() - start < 45:
            for model in models_to_try:
                if model in rate_limited:
                    if expirations.get(model, 0) <= time.time():
                        rate_limited.discard(model)
                    else:
                        continue
                try:
                    return self.generate(model, messages, **kwargs)
                except Exception:
                    rate_limited.add(model)
                    expirations[model] = time.time() + 60

        raise RuntimeError(f"All models failed: {models_to_try}")

    async def agenerate_with_fallbacks(
        self,
        primary_model: str,
        messages: Sequence[dict[str, Any]],
        fallbacks: list[str] | None = None,
        **kwargs: Any,
    ) -> GenerationResponse:
        models_to_try = [primary_model] + (fallbacks or [])
        rate_limited: set[str] = set()
        expirations: dict[str, float] = {}
        start = time.time()

        while time.time() - start < 45:
            for model in models_to_try:
                if model in rate_limited:
                    if expirations.get(model, 0) <= time.time():
                        rate_limited.discard(model)
                    else:
                        continue
                try:
                    return await self.agenerate(model, messages, **kwargs)
                except Exception:
                    rate_limited.add(model)
                    expirations[model] = time.time() + 60

        raise RuntimeError(f"All models failed: {models_to_try}")
