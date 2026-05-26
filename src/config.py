"""
config.py
---------
Central configuration module for the AI Code Reviewer.

Responsibilities:
  - Load all settings from environment variables (no hard-coded secrets).
  - Expose model name constants and the system prompt used for AI inference.
  - Provide a validate() function that fails fast with clear error messages
    when required variables are absent.

No business logic lives here — only configuration.
"""

import os

# ---------------------------------------------------------------------------
# GitHub settings
# ---------------------------------------------------------------------------

# Personal-access token or GITHUB_TOKEN secret injected by GitHub Actions.
GITHUB_TOKEN: str | None = os.environ.get("GITHUB_TOKEN")

# Full repository name in "owner/repo" format (e.g. "acme/my-service").
GITHUB_REPOSITORY: str | None = os.environ.get("GITHUB_REPOSITORY")

# Pull-request number as a string; callers should cast to int when needed.
PR_NUMBER: str | None = os.environ.get("PR_NUMBER")

# ---------------------------------------------------------------------------
# AI provider settings
# ---------------------------------------------------------------------------

# Which AI backend to use.  Supported values: "claude" | "openai" | "openrouter".
# Defaults to "claude" if not set.
AI_PROVIDER: str = os.environ.get("AI_PROVIDER", "claude")

# API key for Anthropic Claude models.
ANTHROPIC_API_KEY: str | None = os.environ.get("ANTHROPIC_API_KEY")

# API key for OpenAI models.
OPENAI_API_KEY: str | None = os.environ.get("OPENAI_API_KEY")

# API key for OpenRouter (https://openrouter.ai).
# OpenRouter provides a unified OpenAI-compatible API that proxies many
# model providers (Anthropic, OpenAI, Meta, Mistral, etc.) under one key.
OPENROUTER_API_KEY: str | None = os.environ.get("OPENROUTER_API_KEY")

# ---------------------------------------------------------------------------
# Reviewer / chunking settings
# ---------------------------------------------------------------------------

# Maximum number of characters sent to the AI in a single request.
# Larger values improve context but increase latency and cost.
MAX_CHUNK_CHARS: int = int(os.environ.get("MAX_CHUNK_CHARS", 3000))

# Maximum number of tokens the AI may generate in its response.
MAX_TOKENS: int = int(os.environ.get("MAX_TOKENS", 1000))

# ---------------------------------------------------------------------------
# Model name constants
# ---------------------------------------------------------------------------

# Anthropic Claude model identifier.
CLAUDE_MODEL: str = "claude-opus-4-5"

# OpenAI model identifier.
OPENAI_MODEL: str = "gpt-4o"

# OpenRouter model identifier.
# Uses OpenRouter's "provider/model" slug format.
# See the full list at: https://openrouter.ai/models
OPENROUTER_MODEL: str = "anthropic/claude-3.5-sonnet"

# OpenRouter base URL — drop-in replacement for the OpenAI base URL.
OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT: str = """
You are an expert code reviewer. Analyze the provided code diff and identify any issues.

Return your findings as a **JSON array** (and nothing else — no prose, no markdown fences).
Each element in the array must be an object with exactly these fields:

  {
    "file":     "<relative path to the file>",
    "line":     <integer line number where the issue occurs>,
    "severity": "<one of: error | warning | suggestion>",
    "message":  "<concise description of the issue>",
    "fix":      "<concrete, actionable suggestion or corrected code snippet>"
  }

Severity guidelines:
  - error      : Bugs, security vulnerabilities, or logic flaws that must be fixed.
  - warning    : Code smells, deprecated patterns, or maintainability concerns.
  - suggestion : Style improvements, readability enhancements, or optional refactors.

If there are no issues, return an empty array: []
""".strip()


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate() -> None:
    """
    Validate that all required environment variables are present.

    Raises:
        EnvironmentError: If one or more required variables are missing,
                          with a descriptive message listing every absent variable.
    """
    missing: list[str] = []

    # --- GitHub variables (always required) ---------------------------------
    if not GITHUB_TOKEN:
        missing.append("GITHUB_TOKEN (GitHub personal-access token or Actions secret)")
    if not GITHUB_REPOSITORY:
        missing.append("GITHUB_REPOSITORY (e.g. 'owner/repo')")
    if not PR_NUMBER:
        missing.append("PR_NUMBER (pull-request number to review)")

    # --- AI provider-specific keys ------------------------------------------
    provider = AI_PROVIDER.lower()

    if provider == "claude":
        if not ANTHROPIC_API_KEY:
            missing.append(
                "ANTHROPIC_API_KEY (required when AI_PROVIDER='claude')"
            )
    elif provider == "openai":
        if not OPENAI_API_KEY:
            missing.append(
                "OPENAI_API_KEY (required when AI_PROVIDER='openai')"
            )
    elif provider == "openrouter":
        if not OPENROUTER_API_KEY:
            missing.append(
                "OPENROUTER_API_KEY (required when AI_PROVIDER='openrouter')"
            )
    else:
        missing.append(
            f"AI_PROVIDER must be 'claude', 'openai', or 'openrouter', "
            f"got: '{AI_PROVIDER}'"
        )

    if missing:
        formatted = "\n  - ".join(missing)
        raise EnvironmentError(
            f"AI Code Reviewer — missing or invalid configuration:\n  - {formatted}\n"
            "Set the above variables before running the reviewer."
        )
