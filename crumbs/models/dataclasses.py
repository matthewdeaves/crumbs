"""Data models for git commit analysis."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class CommitType(Enum):
    """Conventional commit types."""

    FEAT = "feat"
    FIX = "fix"
    DOCS = "docs"
    STYLE = "style"
    REFACTOR = "refactor"
    PERF = "perf"
    TEST = "test"
    BUILD = "build"
    CI = "ci"
    CHORE = "chore"
    REVERT = "revert"
    UNKNOWN = "unknown"


@dataclass
class CommitStats:
    """Statistics for a single commit's changes."""

    lines_added: int = 0
    lines_deleted: int = 0
    files_changed: int = 0

    @property
    def total_changes(self) -> int:
        """Total lines changed (added + deleted)."""
        return self.lines_added + self.lines_deleted

    @property
    def size_bucket(self) -> str:
        """Categorize commit by size."""
        total = self.total_changes
        if total <= 10:
            return "small"
        elif total <= 50:
            return "medium"
        elif total <= 200:
            return "large"
        else:
            return "xlarge"


@dataclass
class Commit:
    """Represents a parsed git commit."""

    sha: str
    message: str
    author: str
    author_email: str
    timestamp: datetime
    stats: CommitStats = field(default_factory=CommitStats)
    commit_type: CommitType = CommitType.UNKNOWN
    scope: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None
    co_authors: list[str] = field(default_factory=list)
    phase: Optional[int] = None
    is_conventional: bool = False


@dataclass
class RepositoryStats:
    """Aggregated statistics for a repository."""

    total_commits: int = 0
    total_lines_added: int = 0
    total_lines_deleted: int = 0
    total_files_changed: int = 0
    commits_by_type: dict[CommitType, int] = field(default_factory=dict)
    commits_by_author: dict[str, int] = field(default_factory=dict)
    commits_by_day: dict[str, int] = field(default_factory=dict)
    commits_by_hour: dict[int, int] = field(default_factory=dict)
    commits_by_phase: dict[int, int] = field(default_factory=dict)
    size_distribution: dict[str, int] = field(default_factory=dict)
    conventional_count: int = 0
    co_authored_count: int = 0
    phases_detected: list[int] = field(default_factory=list)
    first_commit_date: Optional[datetime] = None
    last_commit_date: Optional[datetime] = None
    avg_commit_interval_hours: float = 0.0
    work_sessions: int = 0

    @property
    def conventional_compliance(self) -> float:
        """Percentage of commits following conventional format."""
        if self.total_commits == 0:
            return 0.0
        return self.conventional_count / self.total_commits

    @property
    def co_authored_percentage(self) -> float:
        """Percentage of commits with co-authors."""
        if self.total_commits == 0:
            return 0.0
        return self.co_authored_count / self.total_commits

    @property
    def total_churn(self) -> int:
        """Total code churn (additions + deletions)."""
        return self.total_lines_added + self.total_lines_deleted
