"""Memory hooks — inject context before session, extract facts after."""

import re
import logging
from datetime import datetime

import config
from memory.search import search, index_note
from memory.vault import read_note, append_note, save_note, list_notes

logger = logging.getLogger("memory.hooks")


def get_memory_context(query: str) -> str | None:
    """Search memory vault, return formatted context string or None.

    Used by both CLI (via inject_context) and API (via backend._build_messages).
    """
    if not config.MEMORY_ENABLED:
        return None

    query_text = re.sub(r'[^\w\s]', ' ', query[:200]).strip()
    if not query_text:
        return None

    results = search(query_text, limit=config.MEMORY_INJECT_LIMIT)
    if not results:
        return None

    context_parts = []
    for r in results:
        content = read_note(r.path)
        if content:
            snippet = content[:500].strip()
            context_parts.append(f"[{r.path}]: {snippet}")

    if not context_parts:
        return None

    logger.info(f"Found {len(context_parts)} memory notes for context")
    return "\n".join(context_parts)


async def inject_context(prompt: str) -> str:
    """For CLI backends: prepend memory context to prompt string."""
    context = get_memory_context(prompt)
    if not context:
        return prompt
    return f"[Memory context:]\n{context}\n\n{prompt}"


async def extract_and_save(user_prompt: str, assistant_response: str):
    """Extract facts from conversation and save to memory vault.

    Uses simple heuristics — no extra CLI call (zero cost).
    """
    if not config.MEMORY_ENABLED:
        return

    # Save session log
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    short_prompt = user_prompt[:50].replace("/", "-").replace("\\", "-").strip()
    log_filename = f"sessions/{timestamp}_{_slugify(short_prompt)}.md"

    log_content = f"# {short_prompt}\n\n"
    log_content += f"**User:** {user_prompt[:500]}\n\n"
    log_content += f"**Assistant:** {assistant_response[:1000]}\n"

    save_note(log_filename, log_content)
    index_note(log_filename, log_content)

    # Extract explicit "remember" requests
    remember_patterns = [
        r"запомни[:\s]+(.+?)(?:\.|$)",
        r"remember[:\s]+(.+?)(?:\.|$)",
        r"сохрани[:\s]+(.+?)(?:\.|$)",
    ]

    for pattern in remember_patterns:
        matches = re.findall(pattern, user_prompt, re.IGNORECASE)
        for match in matches:
            fact = match.strip()
            if len(fact) > 10:
                append_note("facts.md", fact)
                index_note("facts.md", fact)
                logger.info(f"Extracted explicit fact: {fact[:60]}...")


def _slugify(text: str) -> str:
    """Convert text to filename-safe slug."""
    text = re.sub(r'[^\w\s-]', '', text.lower())
    text = re.sub(r'[\s]+', '-', text)
    return text[:40]
