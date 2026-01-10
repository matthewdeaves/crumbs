"""Configuration constants for crumbs."""

import os

from dotenv import load_dotenv

# Load .env file from project root
load_dotenv()

# Commit size thresholds (total lines changed)
SIZE_THRESHOLDS = {
    "small": 10,
    "medium": 50,
    "large": 200,
    # xlarge is anything above large
}

# Work session gap threshold (minutes)
SESSION_GAP_MINUTES = 30

# Conventional commit types
CONVENTIONAL_TYPES = [
    "feat",
    "fix",
    "docs",
    "style",
    "refactor",
    "perf",
    "test",
    "build",
    "ci",
    "chore",
    "revert",
]

# LLM Settings (OpenRouter)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "anthropic/claude-3-haiku")
SENTIMENT_BATCH_SIZE = int(os.getenv("SENTIMENT_BATCH_SIZE", "5"))
LLM_AVAILABLE = bool(OPENROUTER_API_KEY)
