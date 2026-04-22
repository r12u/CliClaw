"""OpenAI Codex CLI backend."""

import json
from typing import Optional

from backends.base import CLIBackend, CLIResult


class CodexBackend(CLIBackend):
    name = "codex"
    display_name = "Codex CLI"
    identity_filename = "IDENTITY.md"

    def build_command(self, prompt: str, session_id: Optional[str] = None) -> list[str]:
        cmd = [self.bin_path, "exec", "--json", "--full-auto", "--skip-git-repo-check"]
        cmd += [prompt]
        return cmd

    def parse_output(self, raw: str) -> Optional[CLIResult]:
        thread_id = None
        final_text_parts = []
    
        for line in raw.strip().splitlines():
            line = line.strip()
            if not line:
                continue
    
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
    
            event_type = data.get("type")
    
            if event_type == "thread.started":
                thread_id = data.get("thread_id")
    
            elif event_type == "item.completed":
                item = data.get("item", {})
                if item.get("type") == "agent_message":
                    text = item.get("text", "")
                    if text:
                        final_text_parts.append(text)
    
        if final_text_parts:
            return CLIResult(
                text="\n\n".join(final_text_parts).strip(),
                session_id=thread_id,
                raw={"thread_id": thread_id},
            )
    
        return None
