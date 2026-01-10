"""Tests for crumbs data models."""

from datetime import datetime, timezone

import pytest

from crumbs.models import Commit, CommitStats, CommitType, RepositoryStats


class TestCommitType:
    """Tests for CommitType enum."""

    def test_all_conventional_types_present(self):
        """Verify all conventional commit types are defined."""
        expected_types = [
            "feat", "fix", "docs", "style", "refactor",
            "perf", "test", "build", "ci", "chore", "revert"
        ]
        for type_name in expected_types:
            assert hasattr(CommitType, type_name.upper())
            assert CommitType[type_name.upper()].value == type_name

    def test_unknown_type_exists(self):
        """Verify UNKNOWN type exists for non-conventional commits."""
        assert CommitType.UNKNOWN.value == "unknown"

    def test_enum_values_are_lowercase(self):
        """All enum values should be lowercase strings."""
        for commit_type in CommitType:
            assert commit_type.value == commit_type.value.lower()


class TestCommitStats:
    """Tests for CommitStats dataclass."""

    def test_default_values(self):
        """CommitStats should have zero defaults."""
        stats = CommitStats()
        assert stats.lines_added == 0
        assert stats.lines_deleted == 0
        assert stats.files_changed == 0

    def test_total_changes_calculation(self):
        """total_changes should sum added and deleted lines."""
        stats = CommitStats(lines_added=100, lines_deleted=50, files_changed=5)
        assert stats.total_changes == 150

    def test_size_bucket_small(self):
        """Commits with <= 10 changes are small."""
        stats = CommitStats(lines_added=5, lines_deleted=3)
        assert stats.size_bucket == "small"

        stats = CommitStats(lines_added=10, lines_deleted=0)
        assert stats.size_bucket == "small"

    def test_size_bucket_medium(self):
        """Commits with 11-50 changes are medium."""
        stats = CommitStats(lines_added=11, lines_deleted=0)
        assert stats.size_bucket == "medium"

        stats = CommitStats(lines_added=25, lines_deleted=25)
        assert stats.size_bucket == "medium"

    def test_size_bucket_large(self):
        """Commits with 51-200 changes are large."""
        stats = CommitStats(lines_added=51, lines_deleted=0)
        assert stats.size_bucket == "large"

        stats = CommitStats(lines_added=100, lines_deleted=100)
        assert stats.size_bucket == "large"

    def test_size_bucket_xlarge(self):
        """Commits with > 200 changes are xlarge."""
        stats = CommitStats(lines_added=201, lines_deleted=0)
        assert stats.size_bucket == "xlarge"

        stats = CommitStats(lines_added=500, lines_deleted=300)
        assert stats.size_bucket == "xlarge"

    def test_fixture_values(self, sample_commit_stats):
        """Verify fixture has expected values."""
        assert sample_commit_stats.lines_added == 50
        assert sample_commit_stats.lines_deleted == 20
        assert sample_commit_stats.total_changes == 70
        assert sample_commit_stats.size_bucket == "large"  # 70 is in 51-200 range


class TestCommit:
    """Tests for Commit dataclass."""

    def test_required_fields_only(self):
        """Commit can be created with only required fields."""
        commit = Commit(
            sha="abc123",
            message="test message",
            author="Test Author",
            author_email="test@example.com",
            timestamp=datetime.now(timezone.utc),
        )
        assert commit.sha == "abc123"
        assert commit.message == "test message"
        assert commit.commit_type == CommitType.UNKNOWN
        assert commit.co_authors == []
        assert commit.phase is None
        assert commit.is_conventional is False

    def test_full_commit(self, sample_commit):
        """Verify sample_commit fixture has all fields populated."""
        assert sample_commit.sha == "abc123def456"
        assert sample_commit.commit_type == CommitType.FEAT
        assert sample_commit.scope == "auth"
        assert sample_commit.subject == "add login functionality"
        assert sample_commit.phase == 3
        assert sample_commit.is_conventional is True
        assert len(sample_commit.co_authors) == 1
        assert "Claude" in sample_commit.co_authors[0]

    def test_minimal_commit(self, minimal_commit):
        """Verify minimal_commit fixture has defaults."""
        assert minimal_commit.sha == "def789abc123"
        assert minimal_commit.stats.total_changes == 0
        assert minimal_commit.commit_type == CommitType.UNKNOWN
        assert minimal_commit.co_authors == []
        assert minimal_commit.is_conventional is False

    def test_commit_stats_access(self, sample_commit):
        """Can access nested stats from commit."""
        assert sample_commit.stats.lines_added == 50
        assert sample_commit.stats.total_changes == 70
        assert sample_commit.stats.size_bucket == "large"  # 70 is in 51-200 range


class TestRepositoryStats:
    """Tests for RepositoryStats dataclass."""

    def test_default_values(self):
        """RepositoryStats should have sensible defaults."""
        stats = RepositoryStats()
        assert stats.total_commits == 0
        assert stats.total_lines_added == 0
        assert stats.commits_by_type == {}
        assert stats.phases_detected == []

    def test_conventional_compliance_empty(self):
        """Compliance should be 0 when no commits."""
        stats = RepositoryStats()
        assert stats.conventional_compliance == 0.0

    def test_conventional_compliance_calculation(self):
        """Compliance should be ratio of conventional to total."""
        stats = RepositoryStats(total_commits=100, conventional_count=75)
        assert stats.conventional_compliance == 0.75

    def test_co_authored_percentage_empty(self):
        """Co-authored percentage should be 0 when no commits."""
        stats = RepositoryStats()
        assert stats.co_authored_percentage == 0.0

    def test_co_authored_percentage_calculation(self):
        """Co-authored percentage should be ratio of co-authored to total."""
        stats = RepositoryStats(total_commits=100, co_authored_count=98)
        assert stats.co_authored_percentage == 0.98

    def test_total_churn_calculation(self):
        """Total churn should sum additions and deletions."""
        stats = RepositoryStats(total_lines_added=5000, total_lines_deleted=2000)
        assert stats.total_churn == 7000

    def test_fixture_values(self, sample_repository_stats):
        """Verify fixture has expected values."""
        assert sample_repository_stats.total_commits == 100
        assert sample_repository_stats.conventional_compliance == 0.75
        assert sample_repository_stats.co_authored_percentage == 0.98
        assert sample_repository_stats.total_churn == 7000
        assert len(sample_repository_stats.phases_detected) == 4
        assert sample_repository_stats.work_sessions == 8
