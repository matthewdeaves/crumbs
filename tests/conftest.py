"""Shared pytest fixtures for crumbs tests."""

from datetime import datetime, timezone

import pytest

from crumbs.models import Commit, CommitStats, CommitType, RepositoryStats


@pytest.fixture
def sample_commit_stats():
    """Sample commit stats with known values."""
    return CommitStats(lines_added=50, lines_deleted=20, files_changed=3)


@pytest.fixture
def sample_commit(sample_commit_stats):
    """Sample commit with full data."""
    return Commit(
        sha="abc123def456",
        message="feat(auth): add login functionality\n\nImplemented OAuth2 flow.\n\nCo-Authored-By: Claude <claude@anthropic.com>",
        author="Test Author",
        author_email="test@example.com",
        timestamp=datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
        stats=sample_commit_stats,
        commit_type=CommitType.FEAT,
        scope="auth",
        subject="add login functionality",
        body="Implemented OAuth2 flow.",
        co_authors=["Claude <claude@anthropic.com>"],
        phase=3,
        is_conventional=True,
    )


@pytest.fixture
def minimal_commit():
    """Commit with only required fields."""
    return Commit(
        sha="def789abc123",
        message="quick fix",
        author="Test Author",
        author_email="test@example.com",
        timestamp=datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
    )


@pytest.fixture
def sample_commits(sample_commit, minimal_commit):
    """List of sample commits for testing."""
    return [sample_commit, minimal_commit]


@pytest.fixture
def sample_repository_stats():
    """Sample repository stats with known values."""
    return RepositoryStats(
        total_commits=100,
        total_lines_added=5000,
        total_lines_deleted=2000,
        total_files_changed=150,
        commits_by_type={
            CommitType.FEAT: 40,
            CommitType.FIX: 30,
            CommitType.DOCS: 15,
            CommitType.TEST: 10,
            CommitType.CHORE: 5,
        },
        commits_by_author={"Author A": 60, "Author B": 40},
        commits_by_day={"2024-01-15": 20, "2024-01-16": 30, "2024-01-17": 50},
        commits_by_hour={9: 10, 10: 20, 11: 25, 14: 30, 15: 15},
        commits_by_phase={1: 20, 2: 30, 3: 25, 4: 25},
        size_distribution={"small": 40, "medium": 35, "large": 20, "xlarge": 5},
        conventional_count=75,
        co_authored_count=98,
        phases_detected=[1, 2, 3, 4],
        first_commit_date=datetime(2024, 1, 15, 8, 0, 0, tzinfo=timezone.utc),
        last_commit_date=datetime(2024, 1, 17, 18, 0, 0, tzinfo=timezone.utc),
        avg_commit_interval_hours=0.5,
        work_sessions=8,
    )
