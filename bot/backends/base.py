"""Backend base classes. Two families: CLI (subprocess) and API (HTTP)."""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger("backend")


@dataclass
class CLIResult:
    """Unified result from any backend (CLI or API)."""
    text: str
    session_id: Optional[str] = None
    num_turns: int = 0
    cost_usd: float = 0.0
    raw: Optional[dict] = None


class Backend(ABC):
    """Abstract base for ALL backends."""

    name: str = "base"
    display_name: str = "Base"

    @abstractmethod
    async def execute(
        self,
        prompt: str,
        session_id: Optional[str] = None,
    ) -> Optional[CLIResult]:
        ...

    def is_api_backend(self) -> bool:
        """True for API backends that manage their own context/history."""
        return False


class CLIBackend(Backend):
    """Base for CLI backends — runs AI tool as subprocess."""

    identity_filename: str = "IDENTITY.md"

    def __init__(self, bin_path: str, work_dir: str, timeout: int = 600):
        self.bin_path = bin_path
        self.work_dir = work_dir
        self.timeout = timeout

    async def execute(
        self,
        prompt: str,
        session_id: Optional[str] = None,
    ) -> Optional[CLIResult]:
        """Run CLI as subprocess and return parsed result."""
        cmd = self.build_command(prompt, session_id)
        logger.info(f"[{self.name}] Running: {' '.join(cmd[:5])}... session={session_id}")

        try:
            from pathlib import Path
            Path(self.work_dir).mkdir(parents=True, exist_ok=True)

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=self.work_dir,
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=self.timeout,
            )

        except asyncio.TimeoutError:
            logger.error(f"[{self.name}] Timed out after {self.timeout}s")
            try:
                proc.kill()
            except ProcessLookupError:
                pass
            return None
        except FileNotFoundError:
            logger.error(f"[{self.name}] Binary not found: {self.bin_path}")
            return None

        raw = stdout.decode("utf-8", errors="replace").strip()
        result = self.parse_output(raw)

        if result is None:
            error = stderr.decode("utf-8", errors="replace").strip()
            if error:
                logger.error(f"[{self.name}] stderr: {error[:300]}")
            if raw:
                logger.warning(f"[{self.name}] No structured output, wrapping raw stdout")
                return CLIResult(text=raw, session_id=session_id)
            return None

        logger.info(f"[{self.name}] Done: turns={result.num_turns}, session={result.session_id}")
        return result

    def build_command(self, prompt: str, session_id: Optional[str] = None) -> list[str]:
        raise NotImplementedError

    def parse_output(self, raw: str) -> Optional[CLIResult]:
        raise NotImplementedError


class APIBackend(Backend):
    """Base for API backends — HTTP calls, manages own context."""

    def __init__(self, api_key: str, work_dir: str, timeout: int = 120, model: str = ""):
        self.api_key = api_key
        self.work_dir = work_dir
        self.timeout = timeout
        self.model = model

    def is_api_backend(self) -> bool:
        return True
