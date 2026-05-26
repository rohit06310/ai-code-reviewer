# AI Code Reviewer

An automated code review bot that uses AI to analyse pull-request diffs and post
inline feedback as GitHub PR comments.

## How it works

```
GitHub PR  →  fetch diff  →  clean & chunk  →  AI review  →  post comments
```

1. **Fetch** — Retrieves the unified diff for the PR from the GitHub REST API.
2. **Filter** — Removes whitespace-only changes, binary notices, and git annotations.
3. **Chunk** — Splits large diffs into pieces that fit within the model's context window.
4. **Review** — Sends each chunk to the configured AI provider and parses the JSON response.
5. **Comment** — Posts each detected issue as a separate PR comment with severity, file, line, and a suggested fix.

## Project structure

```
ai-code-reviewer/
├── .github/
│   └── workflows/
│       └── review.yml          # GitHub Actions — triggers on pull_request
├── src/
│   ├── __init__.py
│   ├── config.py               # All env vars, constants, system prompt
│   ├── fetcher.py              # GitHub API → raw diff string
│   ├── chunker.py              # Raw diff → cleaned, sized chunks
│   ├── reviewer.py             # Chunks → AI → list of issues
│   └── commenter.py            # Issues → GitHub PR comments
├── sample_bad_code/
│   └── bad_example.py          # Intentionally flawed file for testing
├── main.py                     # Pipeline entry point
├── requirements.txt
└── README.md
```

## Supported AI providers

| `AI_PROVIDER` | SDK needed | Key variable |
|---|---|---|
| `openrouter` | `openai` | `OPENROUTER_API_KEY` |
| `claude` | `anthropic` | `ANTHROPIC_API_KEY` |
| `openai` | `openai` | `OPENAI_API_KEY` |

OpenRouter is recommended — one key gives access to Claude, GPT-4o, Llama, Mistral, and more.
Browse models at [openrouter.ai/models](https://openrouter.ai/models).

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment variables

Copy `.env` and fill in your values:

```env
# GitHub
GITHUB_TOKEN=ghp_your_token_here
GITHUB_REPOSITORY=owner/repo
PR_NUMBER=42

# AI provider
AI_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-v1-your-key-here
```

> **Never commit `.env` to version control.** It is listed in `.gitignore`.

### 3. Run locally

```bash
python main.py
```

## GitHub Actions setup

The workflow in `.github/workflows/review.yml` runs automatically on every pull request.

Add your API key as a repository secret:

1. Go to **Settings → Secrets and variables → Actions**
2. Click **New repository secret**
3. Name: `OPENROUTER_API_KEY` (or `ANTHROPIC_API_KEY` / `OPENAI_API_KEY`)
4. Value: your API key

The `GITHUB_TOKEN` secret is provided automatically by GitHub Actions — no setup needed.

## Testing with sample bad code

`sample_bad_code/bad_example.py` contains 10 deliberate issues including hardcoded
secrets, SQL injection, mutable default arguments, bare excepts, and resource leaks.

Open a pull request that adds this file to trigger the reviewer and verify it works
end-to-end.

## Issue format

Each AI-detected issue is posted as a PR comment in this format:

```
🔴 Error: `app.py` — Line 42

SQL query built with string formatting is vulnerable to injection.

Suggested fix:
```python
cursor.execute("SELECT * FROM users WHERE name = ?", (username,))
```
---
*Posted by AI Code Reviewer*
```

Severity levels: 🔴 Error · 🟡 Warning · 🔵 Suggestion

## Configuration reference

| Variable | Default | Description |
|---|---|---|
| `AI_PROVIDER` | `claude` | `claude`, `openai`, or `openrouter` |
| `MAX_CHUNK_CHARS` | `3000` | Max characters per AI request |
| `MAX_TOKENS` | `1000` | Max tokens in AI response |
| `OPENROUTER_MODEL` | *(see config.py)* | OpenRouter model slug |
| `CLAUDE_MODEL` | *(see config.py)* | Anthropic model identifier |
| `OPENAI_MODEL` | *(see config.py)* | OpenAI model identifier |
