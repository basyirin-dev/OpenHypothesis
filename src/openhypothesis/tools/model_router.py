"""LiteLLM-based model router with sync/async generation and cascading fallbacks.

Wraps ``litellm.completion`` / ``litellm.acompletion`` to provide:
- Structured ``GenerationResponse`` and ``CostRecord`` types.
- Rate-limit-aware fallback across a priority-ordered list of models.
- Async streaming support.

The retry/cooldown behaviour is governed by ``RouterConfig``.
"""
import time
from collections.abc import AsyncGenerator, Sequence
from typing import Any

from litellm import acompletion, completion, completion_cost
from pydantic import BaseModel

from openhypothesis.config.schema import RouterConfig
from openhypothesis.config.settings import Settings


class CostRecord(BaseModel):
    """Token usage and estimated dollar cost for a single model invocation."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    model: str = ""


class GenerationResponse(BaseModel):
    """Structured output from a model generation call."""

    content: str
    cost: CostRecord
    model_used: str
    finish_reason: str = ""


class ModelRouter:
    """Router that wraps LiteLLM for structured generation with fallback support.

    Usage::

        router = ModelRouter()
        resp = router.generate("openai/gpt-4o", messages=[...])
        resp = await router.agenerate_with_fallbacks(
            "openai/gpt-4o", messages=[...], fallbacks=["openai/gpt-4o-mini"]
        )
    """

    def __init__(
        self,
        settings: Settings | None = None,
        router_config: RouterConfig | None = None,
    ) -> None:
        """Configure the router with global timeout and retry settings.

        Args:
            settings: ``Settings`` instance (auto-created if omitted).
            router_config: Override router settings; falls back to
                ``settings.app_config.router``.
        """
        self._settings = settings or Settings()
        cfg = router_config or self._settings.app_config.router
        import litellm as _litellm

        _litellm.request_timeout = cfg.request_timeout  # type: ignore[attr-defined]
        _litellm.num_retries_on_timeout = cfg.num_retries_on_timeout

    @staticmethod
    def _extract_cost(response: Any) -> CostRecord:
        """Parse token usage and cost from a LiteLLM response object.

        Falls back gracefully if the response lacks usage data or the cost
        calculation fails (e.g. unmapped model).
        """
        usage = getattr(response, "usage", None)
        if usage is None:
            return CostRecord(model=getattr(response, "model", ""))
        try:
            cost = completion_cost(completion_response=response)
        except (ValueError, KeyError, TypeError):
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
        """Synchronous generation via ``litellm.completion``."""
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
        """Asynchronous generation via ``litellm.acompletion``."""
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
        """Async streaming generator that yields content tokens as they arrive."""
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
        """Synchronous generation with cascading fallback across models.

        Iterates through the model list (primary first, then fallbacks) for up
        to 45 seconds. If a model raises a rate-limit or server error, it is
        cooled down for 60 seconds before being retried.

        Args:
            primary_model: Preferred model identifier.
            messages: Chat messages to send.
            fallbacks: Ordered list of fallback model identifiers.

        Raises:
            RuntimeError: If all models fail within the 45-second window.
            litellm.AuthenticationError: If an API key is missing or invalid.
            litellm.InvalidRequestError: If the request parameters are invalid.
        """
        from litellm.exceptions import AuthenticationError, InvalidRequestError

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
                except AuthenticationError:
                    raise
                except InvalidRequestError:
                    raise
                except Exception:
                    rate_limited.add(model)
                    expirations[model] = time.time() + 60

        raise RuntimeError(
            f"All models failed within 45s: {models_to_try}. "
            "Check API keys, network, and model availability."
        )

    async def agenerate_with_fallbacks(
        self,
        primary_model: str,
        messages: Sequence[dict[str, Any]],
        fallbacks: list[str] | None = None,
        **kwargs: Any,
    ) -> GenerationResponse:
        """Async version of ``generate_with_fallbacks``.

        See ``generate_with_fallbacks`` for parameter and exception docs.
        """
        from litellm.exceptions import AuthenticationError, InvalidRequestError

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
                except AuthenticationError:
                    raise
                except InvalidRequestError:
                    raise
                except Exception:
                    rate_limited.add(model)
                    expirations[model] = time.time() + 60

        raise RuntimeError(
            f"All models failed within 45s: {models_to_try}. "
            "Check API keys, network, and model availability."
        )
