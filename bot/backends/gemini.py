"""Google Gemini CLI backend."""

import json
from typing import Optional

from backends.base import CLIBackend, CLIResult


class GeminiBackend(CLIBackend):
    name = "gemini"
    display_name = "Gemini CLI"
    identity_filename = "GEMINI.md"

    def build_command(self, prompt: str, session_id: Optional[str] = None) -> list[str]:
        cmd = [self.bin_path, "-p", prompt, "--output-format", "json"]
        cmd += ["-y"]  # auto-approve (like --yolo)
        if session_id:
            cmd += ["--resume", session_id]
        return cmd

    def parse_output(self, raw: str) -> Optional[CLIResult]:
        """Gemini outputs streaming JSONL with {type:result} at the end."""
        # Try JSON array first
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                for item in reversed(data):
                    if isinstance(item, dict) and item.get("type") == "result":
                        return CLIResult(
                            text=item.get("response", item.get("result", "")),
                            session_id=item.get("session_id"),
                            num_turns=item.get("num_turns", 0),
                            raw=item,
                        )
            elif isinstance(data, dict):
                # Single JSON object format
                if "response" in data:
                    return CLIResult(
                        text=data["response"],
                        session_id=data.get("session_id"),
                        raw=data,
                    )
                if "result" in data:
                    return CLIResult(
                        text=data["result"],
                        session_id=data.get("session_id"),
                        raw=data,
                    )
        except json.JSONDecodeError:
            pass

        # Fallback: line-by-line JSONL (streaming format)
        last_result = None
        for line in raw.strip().split("\n"):
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                data = json.loads(line)
                if data.get("type") == "result":
                    last_result = CLIResult(
                        text=data.get("response", data.get("result", "")),
                        session_id=data.get("session_id"),
                        num_turns=data.get("num_turns", 0),
                        raw=data,
                    )
                elif "response" in data or "result" in data:
                    last_result = CLIResult(
                        text=data.get("response", data.get("result", "")),
                        session_id=data.get("session_id"),
                        raw=data,
                    )
            except json.JSONDecodeError:
                continue

        return last_result
