"""Configuration constants for crumbs."""

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
