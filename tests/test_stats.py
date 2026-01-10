"""Tests for the analysis module."""

from datetime import datetime, timedelta, timezone

import pytest

from crumbs.models import Commit, CommitStats, CommitType
from crumbs.analysis import StatsCalculator, SemanticAnalyzer, MessageQuality


class TestStatsCalculator:
    """Tests for StatsCalculator."""

    def test_empty_commits(self):
        """Calculator handles empty commit list."""
        calc = StatsCalculator([])
        stats = calc.calculate()

        assert stats.total_commits == 0
        assert stats.conventional_compliance == 0.0
        assert stats.co_authored_percentage == 0.0

    def test_total_commits(self, sample_commits):
        """Calculator counts total commits."""
        calc = StatsCalculator(sample_commits)
        assert calc.total_commits == 2

    def test_conventional_compliance(self, sample_commits):
        """Calculator calculates conventional compliance percentage."""
        calc = StatsCalculator(sample_commits)
        # sample_commit is conventional, minimal_commit is not
        assert calc.conventional_compliance == 0.5

    def test_commits_by_type(self, sample_commits):
        """Calculator aggregates commits by type."""
        calc = StatsCalculator(sample_commits)
        stats = calc.calculate()

        assert stats.commits_by_type[CommitType.FEAT] == 1
        assert stats.commits_by_type[CommitType.UNKNOWN] == 1

    def test_commits_by_author(self, sample_commits):
        """Calculator aggregates commits by author."""
        calc = StatsCalculator(sample_commits)
        stats = calc.calculate()

        assert stats.commits_by_author["Test Author"] == 2

    def test_commits_by_day(self, sample_commits):
        """Calculator aggregates commits by day."""
        calc = StatsCalculator(sample_commits)
        stats = calc.calculate()

        assert "2024-01-15" in stats.commits_by_day
        assert stats.commits_by_day["2024-01-15"] == 2

    def test_commits_by_hour(self, sample_commits):
        """Calculator aggregates commits by hour."""
        calc = StatsCalculator(sample_commits)
        stats = calc.calculate()

        # sample_commit at 10:30, minimal_commit at 12:00
        assert stats.commits_by_hour[10] == 1
        assert stats.commits_by_hour[12] == 1

    def test_size_distribution(self, sample_commits):
        """Calculator calculates size distribution."""
        calc = StatsCalculator(sample_commits)
        stats = calc.calculate()

        # sample_commit has 70 total changes (large: 51-200)
        # minimal_commit has 0 changes (small: <= 10)
        assert "large" in stats.size_distribution
        assert "small" in stats.size_distribution

    def test_co_authored_count(self, sample_commits):
        """Calculator counts co-authored commits."""
        calc = StatsCalculator(sample_commits)
        stats = calc.calculate()

        # Only sample_commit has co-authors
        assert stats.co_authored_count == 1
        assert stats.co_authored_percentage == 0.5

    def test_phase_detection(self, sample_commit):
        """Calculator detects phases in commits."""
        calc = StatsCalculator([sample_commit])
        stats = calc.calculate()

        assert 3 in stats.phases_detected
        assert stats.commits_by_phase[3] == 1

    def test_date_range(self, sample_commits):
        """Calculator tracks first and last commit dates."""
        calc = StatsCalculator(sample_commits)
        stats = calc.calculate()

        assert stats.first_commit_date == datetime(
            2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc
        )
        assert stats.last_commit_date == datetime(
            2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc
        )

    def test_average_interval(self):
        """Calculator computes average time between commits."""
        base_time = datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        commits = [
            Commit(
                sha="a",
                message="first",
                author="Test",
                author_email="test@example.com",
                timestamp=base_time,
            ),
            Commit(
                sha="b",
                message="second",
                author="Test",
                author_email="test@example.com",
                timestamp=base_time + timedelta(hours=2),
            ),
            Commit(
                sha="c",
                message="third",
                author="Test",
                author_email="test@example.com",
                timestamp=base_time + timedelta(hours=4),
            ),
        ]

        calc = StatsCalculator(commits)
        stats = calc.calculate()

        # Average of 2 hours between each pair
        assert stats.avg_commit_interval_hours == 2.0

    def test_work_session_detection(self):
        """Calculator detects work sessions based on gaps."""
        base_time = datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        commits = [
            # Session 1: close together
            Commit(
                sha="a",
                message="first",
                author="Test",
                author_email="test@example.com",
                timestamp=base_time,
            ),
            Commit(
                sha="b",
                message="second",
                author="Test",
                author_email="test@example.com",
                timestamp=base_time + timedelta(minutes=30),
            ),
            # Gap of 3 hours - new session
            Commit(
                sha="c",
                message="third",
                author="Test",
                author_email="test@example.com",
                timestamp=base_time + timedelta(hours=3, minutes=30),
            ),
            Commit(
                sha="d",
                message="fourth",
                author="Test",
                author_email="test@example.com",
                timestamp=base_time + timedelta(hours=4),
            ),
        ]

        calc = StatsCalculator(commits)
        stats = calc.calculate()

        assert stats.work_sessions == 2

    def test_total_lines_and_files(self, sample_commit):
        """Calculator aggregates line and file stats."""
        calc = StatsCalculator([sample_commit])
        stats = calc.calculate()

        assert stats.total_lines_added == 50
        assert stats.total_lines_deleted == 20
        assert stats.total_files_changed == 3
        assert stats.total_churn == 70

    def test_stats_caching(self, sample_commits):
        """Calculator caches results."""
        calc = StatsCalculator(sample_commits)

        stats1 = calc.calculate()
        stats2 = calc.calculate()

        # Should return same object
        assert stats1 is stats2


class TestSemanticAnalyzer:
    """Tests for SemanticAnalyzer."""

    def test_conventional_compliance_valid(self):
        """Analyzer recognizes valid conventional commits."""
        analyzer = SemanticAnalyzer()

        assert analyzer.check_compliance("feat: add new feature")
        assert analyzer.check_compliance("fix(auth): resolve login bug")
        assert analyzer.check_compliance("docs: update README")
        assert analyzer.check_compliance("refactor(core): simplify logic")

    def test_conventional_compliance_invalid(self):
        """Analyzer rejects non-conventional messages."""
        analyzer = SemanticAnalyzer()

        assert not analyzer.check_compliance("Add new feature")
        assert not analyzer.check_compliance("Fixed bug")
        assert not analyzer.check_compliance("WIP")
        assert not analyzer.check_compliance("")

    def test_sentiment_positive(self):
        """Analyzer scores positive sentiment messages."""
        analyzer = SemanticAnalyzer()

        score = analyzer.score_sentiment("feat: add and implement new feature")
        assert score > 0

    def test_sentiment_negative(self):
        """Analyzer scores negative sentiment messages."""
        analyzer = SemanticAnalyzer()

        score = analyzer.score_sentiment("fix: workaround for bug issue")
        assert score < 0

    def test_sentiment_neutral(self):
        """Analyzer scores neutral messages."""
        analyzer = SemanticAnalyzer()

        score = analyzer.score_sentiment("chore: run linter")
        assert score == 0.0

    def test_sentiment_empty(self):
        """Analyzer handles empty messages."""
        analyzer = SemanticAnalyzer()

        score = analyzer.score_sentiment("")
        assert score == 0.0

    def test_specificity_vague(self):
        """Analyzer penalizes vague messages."""
        analyzer = SemanticAnalyzer()

        vague_score = analyzer.score_specificity("update stuff")
        specific_score = analyzer.score_specificity(
            "feat(auth): implement OAuth2 authentication flow for UserService"
        )

        assert vague_score < specific_score

    def test_specificity_with_identifiers(self):
        """Analyzer rewards messages with code identifiers."""
        analyzer = SemanticAnalyzer()

        score = analyzer.score_specificity("fix: resolve issue in UserService module")
        assert score > 0.5  # Should be above average

    def test_specificity_empty(self):
        """Analyzer handles empty messages."""
        analyzer = SemanticAnalyzer()

        score = analyzer.score_specificity("")
        assert score == 0.0

    def test_analyze_returns_message_quality(self):
        """Analyzer.analyze returns MessageQuality object."""
        analyzer = SemanticAnalyzer()

        quality = analyzer.analyze("feat: add user authentication")

        assert isinstance(quality, MessageQuality)
        assert quality.is_conventional is True
        assert -1.0 <= quality.sentiment_score <= 1.0
        assert 0.0 <= quality.specificity_score <= 1.0

    def test_message_quality_overall_score(self):
        """MessageQuality computes overall score correctly."""
        # Conventional with positive sentiment and good specificity
        quality = MessageQuality(
            is_conventional=True,
            sentiment_score=1.0,
            specificity_score=0.8,
        )

        # 0.4 (conventional) + 0.2 (max sentiment) + 0.32 (0.8 * 0.4)
        expected = 0.4 + 0.2 + 0.32
        assert abs(quality.overall_score - expected) < 0.01

    def test_analyze_commits_empty(self):
        """Analyzer handles empty commit list."""
        analyzer = SemanticAnalyzer()

        result = analyzer.analyze_commits([])

        assert result["total_analyzed"] == 0
        assert result["conventional_percentage"] == 0.0

    def test_analyze_commits(self, sample_commits):
        """Analyzer computes aggregate metrics for commits."""
        analyzer = SemanticAnalyzer()

        result = analyzer.analyze_commits(sample_commits)

        assert result["total_analyzed"] == 2
        # sample_commit is conventional, minimal_commit is not
        assert result["conventional_count"] == 1
        assert result["conventional_percentage"] == 0.5


class TestCommitSizeBucket:
    """Tests for commit size bucketing (from CommitStats model)."""

    def test_small_bucket(self):
        """Commits with <= 10 changes are small."""
        stats = CommitStats(lines_added=5, lines_deleted=3, files_changed=1)
        assert stats.size_bucket == "small"

    def test_medium_bucket(self):
        """Commits with 11-50 changes are medium."""
        stats = CommitStats(lines_added=30, lines_deleted=15, files_changed=3)
        assert stats.size_bucket == "medium"

    def test_large_bucket(self):
        """Commits with 51-200 changes are large."""
        stats = CommitStats(lines_added=100, lines_deleted=50, files_changed=10)
        assert stats.size_bucket == "large"

    def test_xlarge_bucket(self):
        """Commits with > 200 changes are xlarge."""
        stats = CommitStats(lines_added=300, lines_deleted=100, files_changed=20)
        assert stats.size_bucket == "xlarge"
