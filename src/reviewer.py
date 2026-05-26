"""
reviewer.py
-----------
Responsible for sending diff chunks to an AI provider and returning a
structured list of code issues.

Single responsibility: given a diff string, call the configured AI backend
and return a parsed list of issue dictionaries.  No GitHub API calls, no
file I/O, no output formatting lives here.
"""

import json
import re

from src import config


# ---------------------------------------------------------------------------
# Private helpers — one per AI provider
# ---------------------------------------------------------------------------

def _review_with_claude(diff_chunk: str) -> str:
    """
    Send *diff_chunk* to Anthropic Claude and return the raw response text.

    The Anthropic client is instantiated per call so the module remains
    import-safe even when the anthropic package is not installed (the
    ImportError surfaces only when this function is actually invoked).

    Args:
        diff_chunk: A single chunk of unified diff text.

    Returns:
        str: Raw text content returned by the model.
    """
    try:
        import anthropic  # type: ignore[import]
    except ImportError as exc:
        raise ImportError(
            "The 'anthropic' package is required when AI_PROVIDER='claude'. "
            "Install it with: pip install anthropic"
        ) from exc

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

    message = client.messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=config.MAX_TOKENS,
        system=config.SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": diff_chunk},
        ],
    )

    # The API returns a list of content blocks; we want the text of the first.
    return message.content[0].text


def _review_with_openai(diff_chunk: str) -> str:
    """
    Send *diff_chunk* to OpenAI and return the raw response text.

    Like the Claude helper, the OpenAI client is instantiated lazily to keep
    the module importable without the openai package installed.

    Args:
        diff_chunk: A single chunk of unified diff text.

    Returns:
        str: Raw text content returned by the model.
    """
    try:
        import openai  # type: ignore[import]
    except ImportError as exc:
        raise ImportError(
            "The 'openai' package is required when AI_PROVIDER='openai'. "
            "Install it with: pip install openai"
        ) from exc

    client = openai.OpenAI(api_key=config.OPENAI_API_KEY)

    response = client.chat.completions.create(
        model=config.OPENAI_MODEL,
        max_tokens=config.MAX_TOKENS,
        messages=[
            {"role": "system", "content": config.SYSTEM_PROMPT},
            {"role": "user", "content": diff_chunk},
        ],
    )

    return response.choices[0].message.content or ""


def _review_with_openrouter(diff_chunk: str) -> str:
    """
    Send *diff_chunk* to a model via OpenRouter and return the raw response.

    OpenRouter exposes an OpenAI-compatible REST API, so we reuse the openai
    SDK and simply swap in the OpenRouter base URL and API key.  This lets the
    project access Claude, GPT-4o, Llama, Mistral, and hundreds of other
    models under a single key without separate SDK dependencies.

    The model is set via config.OPENROUTER_MODEL using OpenRouter's
    "provider/model" slug format (e.g. "anthropic/claude-3.5-sonnet").
    See the full model list at: https://openrouter.ai/models

    Args:
        diff_chunk: A single chunk of unified diff text.

    Returns:
        str: Raw text content returned by the model.
    """
    try:
        import openai  # type: ignore[import]
    except ImportError as exc:
        raise ImportError(
            "The 'openai' package is required when AI_PROVIDER='openrouter'. "
            "Install it with: pip install openai"
        ) from exc

    client = openai.OpenAI(
        api_key=config.OPENROUTER_API_KEY,
        base_url=config.OPENROUTER_BASE_URL,
    )

    response = client.chat.completions.create(
        model=config.OPENROUTER_MODEL,
        max_tokens=config.MAX_TOKENS,
        messages=[
            {"role": "system", "content": config.SYSTEM_PROMPT},
            {"role": "user", "content": diff_chunk},
        ],
    )

    return response.choices[0].message.content or ""


# ---------------------------------------------------------------------------
# Markdown fence stripper
# ---------------------------------------------------------------------------

# Matches optional ```json or ``` opening fence and closing ```.
# re.DOTALL makes '.' match newlines so the entire block is captured.
_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.DOTALL)


def _strip_fences(text: str) -> str:
    """
    Remove Markdown code fences that some models wrap around JSON output.

    Example input:
        ```json
        [{"file": "app.py", ...}]
        ```

    Returns the inner content unchanged if no fences are present.

    Args:
        text: Raw model response.

    Returns:
        str: Response with fences removed, ready for json.loads().
    """
    match = _FENCE_RE.match(text)
    return match.group(1) if match else text.strip()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def review_chunk(diff_chunk: str) -> list[dict]:
    """
    Review a single diff chunk and return a list of structured issue dicts.

    Dispatch flow:
      1. Call the appropriate private helper based on config.AI_PROVIDER.
      2. Strip any Markdown code fences from the response.
      3. Parse the result as JSON.
      4. Return the list of issues (empty list on any failure).

    Each issue dict is expected to have the shape defined in config.SYSTEM_PROMPT:
        {
            "file":     str,
            "line":     int,
            "severity": "error" | "warning" | "suggestion",
            "message":  str,
            "fix":      str,
        }

    Args:
        diff_chunk: A single chunk of unified diff text.

    Returns:
        list[dict]: Parsed list of issue dictionaries, or [] on failure.
    """
    provider = config.AI_PROVIDER.lower()

    # --- Call the AI provider -----------------------------------------------
    try:
        if provider == "claude":
            raw_response = _review_with_claude(diff_chunk)
        elif provider == "openai":
            raw_response = _review_with_openai(diff_chunk)
        elif provider == "openrouter":
            raw_response = _review_with_openrouter(diff_chunk)
        else:
            print(
                f"[reviewer] WARNING: Unknown AI_PROVIDER '{config.AI_PROVIDER}'. "
                "Skipping chunk."
            )
            return []
    except Exception as exc:  # noqa: BLE001
        print(f"[reviewer] WARNING: AI API call failed — {exc}")
        return []

    # --- Clean and parse the response ----------------------------------------
    cleaned = _strip_fences(raw_response)

    try:
        issues = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        print(
            f"[reviewer] WARNING: Could not parse AI response as JSON — {exc}\n"
            f"           Raw response (first 200 chars): {cleaned[:200]!r}"
        )
        return []

    # Guard against the model returning a non-list (e.g. a plain dict).
    if not isinstance(issues, list):
        print(
            "[reviewer] WARNING: AI response parsed successfully but is not a "
            f"list (got {type(issues).__name__}). Skipping chunk."
        )
        return []

    return issues


def review_all_chunks(chunks: list[str]) -> list[dict]:
    """
    Review every chunk in *chunks* and return the combined list of issues.

    Progress is printed for each chunk so callers (or CI logs) can track
    long-running reviews without apparent stalls.

    Args:
        chunks: Ordered list of diff chunks produced by chunker.chunk_diff().

    Returns:
        list[dict]: All issues found across every chunk, in order.
    """
    total_chunks = len(chunks)
    all_issues: list[dict] = []

    for index, chunk in enumerate(chunks, start=1):
        print(f"[reviewer] Reviewing chunk {index}/{total_chunks} ...")

        chunk_issues = review_chunk(chunk)
        issue_count = len(chunk_issues)

        print(
            f"[reviewer] Chunk {index}/{total_chunks} complete — "
            f"{issue_count} issue(s) found."
        )

        all_issues.extend(chunk_issues)

    print(
        f"[reviewer] Done. {len(all_issues)} total issue(s) found "
        f"across {total_chunks} chunk(s)."
    )

    return all_issues
