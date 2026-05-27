from pydantic import BaseModel, ConfigDict, Field


class CapabilityReport(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    supports_tool_calling: bool = False
    supports_json_mode: bool = False
    max_context_length: int = Field(default=4096, alias="max_context_length")
    supports_streaming: bool = True
    provider: str = ""


_MODEL_CAPABILITIES: dict[str, CapabilityReport] = {}


def _get_provider(model_id: str) -> str:
    return model_id.split("/")[0] if "/" in model_id else "unknown"


def _lookup_known_capabilities(model_id: str) -> CapabilityReport:
    provider = _get_provider(model_id)

    known_tool_callers = {
        "gpt-4", "gpt-3.5-turbo", "claude-3", "claude-sonnet", "claude-opus",
        "gemini-1.5", "gemini-2.0", "gemini-2.5", "command-r", "command-r+",
        "mistral-large", "llama-3.1", "llama-3.2", "llama-3.3", "llama-4",
        "qwen2.5", "qwen3", "deepseek-chat", "deepseek-v3",
    }
    known_json_mode = {
        "gpt-4", "gpt-3.5-turbo", "gemini-1.5", "gemini-2.0",
        "claude-3", "claude-sonnet-4", "mistral-large",
    }

    model_name = model_id.split("/")[-1] if "/" in model_id else model_id
    supports_tc = any(tag in model_name.lower() for tag in known_tool_callers)
    supports_jm = any(tag in model_name.lower() for tag in known_json_mode)

    if provider == "ollama":
        supports_tc = True
        supports_jm = True

    return CapabilityReport(
        supports_tool_calling=supports_tc,
        supports_json_mode=supports_jm,
        max_context_length=_get_context_window(model_name),
        supports_streaming=True,
        provider=provider,
    )


def _get_context_window(model_name: str) -> int:
    contexts: dict[str, int] = {
        "gpt-4o": 128000, "gpt-4": 8192, "gpt-3.5-turbo": 16385,
        "claude-opus-4": 200000, "claude-sonnet-4": 200000, "claude-haiku-3": 200000,
        "gemini-2.0-flash": 1048576, "gemini-1.5-pro": 2097152,
        "llama-3.1-8b": 131072, "llama-3.1-70b": 131072, "llama-3.1-405b": 131072,
        "llama-4-scout": 10485760, "llama-4-maverick": 1048576,
        "qwen2.5-7b": 32768, "qwen2.5-72b": 131072, "qwen3-235b": 131072,
        "mistral-large": 131072, "deepseek-chat": 65536, "deepseek-v3": 65536,
        "command-r": 131072, "command-r+": 131072,
    }
    for key, ctx in contexts.items():
        if key in model_name.lower():
            return ctx
    return 4096


async def check_capabilities(model_id: str) -> CapabilityReport:
    cached = _MODEL_CAPABILITIES.get(model_id)
    if cached is not None:
        return cached

    report = _lookup_known_capabilities(model_id)
    _MODEL_CAPABILITIES[model_id] = report
    return report
