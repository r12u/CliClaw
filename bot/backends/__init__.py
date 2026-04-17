"""Backend factory."""

from backends.base import Backend, CLIBackend, APIBackend, CLIResult
from backends.claude import ClaudeBackend
from backends.codex import CodexBackend
from backends.gemini import GeminiBackend
from backends.openrouter import OpenRouterBackend

CLI_BACKENDS = {
    "claude": ClaudeBackend,
    "gemini": GeminiBackend,
    "codex": CodexBackend,
}

API_BACKENDS = {
    "openrouter": OpenRouterBackend,
}

ALL_BACKENDS = {**CLI_BACKENDS, **API_BACKENDS}


def get_backend(name: str, **kwargs) -> Backend:
    """Create backend by name. CLI backends need bin_path; API backends need api_key."""
    cls = ALL_BACKENDS.get(name)
    if not cls:
        available = ", ".join(ALL_BACKENDS.keys())
        raise ValueError(f"Unknown backend: {name}. Available: {available}")

    if issubclass(cls, CLIBackend):
        return cls(
            bin_path=kwargs.get("bin_path", ""),
            work_dir=kwargs.get("work_dir", "."),
            timeout=kwargs.get("timeout", 600),
        )
    elif issubclass(cls, APIBackend):
        return cls(
            api_key=kwargs.get("api_key", ""),
            work_dir=kwargs.get("work_dir", "."),
            timeout=kwargs.get("timeout", 120),
            model=kwargs.get("model", ""),
        )
    else:
        raise ValueError(f"Backend {name} has unknown type")
