"""Convert raw syllabus text to structured markdown via Claude Haiku."""

import logging
from pathlib import Path

import anthropic

from config import settings

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT_PATH = Path(__file__).parent.parent.parent / "SYLLABUS_TEMPLATE.md"


def _load_system_prompt() -> str:
    """Extract the system prompt block from SYLLABUS_TEMPLATE.md."""
    raw = _SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
    # Content between the first ```...``` block after "## System Prompt"
    start = raw.index("## System Prompt") + len("## System Prompt")
    block_start = raw.index("```", start) + 3
    block_end = raw.index("```", block_start)
    return raw[block_start:block_end].strip()


_SYSTEM_PROMPT = _load_system_prompt()
_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)


def preprocess_syllabus(raw_text: str) -> tuple[str, dict]:
    """
    Send raw syllabus text to Claude and return structured markdown.

    Returns:
        (processed_markdown, usage_stats) where usage_stats has input/output token counts.
    """
    user_prompt = (
        "Here is the raw text from a course syllabus. "
        "Convert it into structured markdown following the template exactly.\n\n"
        f"RAW SYLLABUS TEXT:\n{raw_text}"
    )

    response = _client.messages.create(
        model=settings.preprocessing_model,
        max_tokens=8192,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    processed = response.content[0].text
    usage = {
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "model": settings.preprocessing_model,
    }
    logger.info("Preprocessing LLM call: %s", usage)

    # Warn if output is much shorter than input — possible data loss
    if len(processed) < len(raw_text) * 0.4:
        logger.warning(
            "Processed markdown (%d chars) is significantly shorter than raw text (%d chars). "
            "Possible data loss.",
            len(processed),
            len(raw_text),
        )

    return processed, usage
