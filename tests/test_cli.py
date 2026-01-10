"""Tests for the CLI module."""

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from crumbs.cli import cli, parse_date
from crumbs.models import Commit, CommitStats, CommitType, RepositoryStats


@pytest.fixture
def runner():
    """Create a CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_commits():
    """Create mock commits for testing."""
    return [
        Commit(
            sha="abc123def456",
            message="feat(auth): add login functionality\n\nCo-Authored-By: Claude <claude@anthropic.com>",
            author="Test Author",
            author_email="test@example.com",
            timestamp=datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
            stats=CommitStats(lines_added=50, lines_deleted=20, files_changed=3),
            commit_type=CommitType.FEAT,
            scope="auth",
            subject="add login functionality",
            co_authors=["Claude <claude@anthropic.com>"],
            is_conventional=True,
        ),
        Commit(
            sha="def789ghi012",
            message="fix(api): resolve null pointer exception",
            author="Test Author",
            author_email="test@example.com",
            timestamp=datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
            stats=CommitStats(lines_added=10, lines_deleted=5, files_changed=1),
            commit_type=CommitType.FIX,
            scope="api",
            subject="resolve null pointer exception",
            is_conventional=True,
        ),
        Commit(
            sha="ghi345jkl678",
            message="quick fix",
            author="Another Author",
            author_email="another@example.com",
            timestamp=datetime(2024, 1, 16, 9, 0, 0, tzinfo=timezone.utc),
            stats=CommitStats(lines_added=5, lines_deleted=2, files_changed=1),
            commit_type=CommitType.UNKNOWN,
            is_conventional=False,
        ),
    ]


@pytest.fixture
def mock_repository(mock_commits):
    """Create a mock GitRepository."""
    repo = MagicMock()
    repo.name = "test-repo"
    repo.iter_commits.return_value = iter(mock_commits)
    return repo


class TestParseDateFunction:
    """Tests for the parse_date helper function."""

    def test_parse_date_none(self):
        """Returns None for None input."""
        assert parse_date(None) is None

    def test_parse_date_valid(self):
        """Parses valid YYYY-MM-DD format."""
        result = parse_date("2024-01-15")
        assert result == datetime(2024, 1, 15, tzinfo=timezone.utc)

    def test_parse_date_with_time(self):
        """Parses date with time component."""
        result = parse_date("2024-01-15T10:30:00")
        assert result == datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)

    def test_parse_date_invalid(self):
        """Raises BadParameter for invalid format."""
        from click import BadParameter

        with pytest.raises(BadParameter):
            parse_date("invalid-date")


class TestCliGroup:
    """Tests for the main CLI group."""

    def test_cli_help(self, runner):
        """CLI shows help message."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Crumbs" in result.output
        assert "analyze" in result.output
        assert "stats" in result.output
        assert "quality" in result.output

    def test_cli_version(self, runner):
        """CLI shows version."""
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0


class TestAnalyzeCommand:
    """Tests for the analyze command."""

    def test_analyze_help(self, runner):
        """Analyze command shows help."""
        result = runner.invoke(cli, ["analyze", "--help"])
        assert result.exit_code == 0
        assert "--output" in result.output
        assert "--format" in result.output
        assert "--since" in result.output
        assert "--author" in result.output

    def test_analyze_nonexistent_path(self, runner):
        """Analyze fails for nonexistent path."""
        result = runner.invoke(cli, ["analyze", "/nonexistent/path"])
        assert result.exit_code != 0

    @patch("crumbs.cli.GitRepository")
    def test_analyze_produces_html(self, mock_repo_class, runner, mock_repository):
        """Analyze produces HTML output file."""
        mock_repo_class.return_value = mock_repository

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            (repo_path / ".git").mkdir()  # Make it look like a git repo

            output_path = repo_path / "report.html"
            result = runner.invoke(
                cli, ["analyze", str(repo_path), "-o", str(output_path)]
            )

            assert result.exit_code == 0
            assert "Report written to" in result.output
            assert output_path.exists()

    @patch("crumbs.cli.GitRepository")
    def test_analyze_produces_json(self, mock_repo_class, runner, mock_repository):
        """Analyze produces JSON output file."""
        mock_repo_class.return_value = mock_repository

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            (repo_path / ".git").mkdir()

            output_path = repo_path / "report.json"
            result = runner.invoke(
                cli,
                ["analyze", str(repo_path), "--format", "json", "-o", str(output_path)],
            )

            assert result.exit_code == 0
            assert "JSON written to" in result.output
            assert output_path.exists()

            # Verify JSON is valid
            content = json.loads(output_path.read_text())
            assert "title" in content
            assert "summary" in content
            assert "charts" in content

    @patch("crumbs.cli.GitRepository")
    def test_analyze_verbose_mode(self, mock_repo_class, runner, mock_repository):
        """Analyze shows verbose output."""
        mock_repo_class.return_value = mock_repository

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            (repo_path / ".git").mkdir()

            result = runner.invoke(cli, ["analyze", str(repo_path), "-v"])

            assert result.exit_code == 0
            assert "Opening repository" in result.output
            assert "Collecting commits" in result.output
            assert "Found" in result.output

    @patch("crumbs.cli.GitRepository")
    def test_analyze_no_commits(self, mock_repo_class, runner):
        """Analyze handles repository with no commits."""
        mock_repo = MagicMock()
        mock_repo.name = "empty-repo"
        mock_repo.iter_commits.return_value = iter([])
        mock_repo_class.return_value = mock_repo

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            (repo_path / ".git").mkdir()

            result = runner.invoke(cli, ["analyze", str(repo_path)])

            assert result.exit_code == 0
            assert "No commits found" in result.output

    @patch("crumbs.cli.GitRepository")
    def test_analyze_with_since_filter(self, mock_repo_class, runner, mock_repository):
        """Analyze passes since filter to repository."""
        mock_repo_class.return_value = mock_repository

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            (repo_path / ".git").mkdir()

            result = runner.invoke(
                cli, ["analyze", str(repo_path), "--since", "2024-01-01"]
            )

            assert result.exit_code == 0
            # Verify iter_commits was called with since parameter
            mock_repository.iter_commits.assert_called_once()
            call_kwargs = mock_repository.iter_commits.call_args[1]
            assert call_kwargs["since"] == datetime(2024, 1, 1, tzinfo=timezone.utc)

    @patch("crumbs.cli.GitRepository")
    def test_analyze_with_author_filter(self, mock_repo_class, runner, mock_repository):
        """Analyze passes author filter to repository."""
        mock_repo_class.return_value = mock_repository

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            (repo_path / ".git").mkdir()

            result = runner.invoke(
                cli, ["analyze", str(repo_path), "--author", "Test Author"]
            )

            assert result.exit_code == 0
            call_kwargs = mock_repository.iter_commits.call_args[1]
            assert call_kwargs["author"] == "Test Author"


class TestStatsCommand:
    """Tests for the stats command."""

    def test_stats_help(self, runner):
        """Stats command shows help."""
        result = runner.invoke(cli, ["stats", "--help"])
        assert result.exit_code == 0
        assert "--verbose" in result.output

    @patch("crumbs.cli.GitRepository")
    def test_stats_output_format(self, mock_repo_class, runner, mock_repository):
        """Stats shows summary table."""
        mock_repo_class.return_value = mock_repository

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            (repo_path / ".git").mkdir()

            result = runner.invoke(cli, ["stats", str(repo_path)])

            assert result.exit_code == 0
            assert "Repository Stats" in result.output
            assert "Total Commits" in result.output
            assert "Lines Added" in result.output
            assert "Conventional Compliance" in result.output

    @patch("crumbs.cli.GitRepository")
    def test_stats_verbose_shows_types(self, mock_repo_class, runner, mock_repository):
        """Stats verbose shows commit type breakdown."""
        mock_repo_class.return_value = mock_repository

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            (repo_path / ".git").mkdir()

            result = runner.invoke(cli, ["stats", str(repo_path), "-v"])

            assert result.exit_code == 0
            assert "Commits by Type" in result.output
            assert "feat" in result.output
            assert "fix" in result.output

    @patch("crumbs.cli.GitRepository")
    def test_stats_no_commits(self, mock_repo_class, runner):
        """Stats handles repository with no commits."""
        mock_repo = MagicMock()
        mock_repo.name = "empty-repo"
        mock_repo.iter_commits.return_value = iter([])
        mock_repo_class.return_value = mock_repo

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            (repo_path / ".git").mkdir()

            result = runner.invoke(cli, ["stats", str(repo_path)])

            assert result.exit_code == 0
            assert "No commits found" in result.output


class TestQualityCommand:
    """Tests for the quality command."""

    def test_quality_help(self, runner):
        """Quality command shows help."""
        result = runner.invoke(cli, ["quality", "--help"])
        assert result.exit_code == 0

    @patch("crumbs.cli.GitRepository")
    def test_quality_output(self, mock_repo_class, runner, mock_repository):
        """Quality shows quality report."""
        mock_repo_class.return_value = mock_repository

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            (repo_path / ".git").mkdir()

            result = runner.invoke(cli, ["quality", str(repo_path)])

            assert result.exit_code == 0
            assert "Commit Quality Report" in result.output
            assert "Conventional Commits" in result.output
            assert "Co-Authored Commits" in result.output
            assert "Overall Grade" in result.output

    @patch("crumbs.cli.GitRepository")
    def test_quality_shows_grade(self, mock_repo_class, runner, mock_repository):
        """Quality shows letter grade."""
        mock_repo_class.return_value = mock_repository

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            (repo_path / ".git").mkdir()

            result = runner.invoke(cli, ["quality", str(repo_path)])

            assert result.exit_code == 0
            # Should have a grade A-F
            assert any(
                grade in result.output for grade in ["Grade: A", "Grade: B", "Grade: C", "Grade: D", "Grade: F"]
            )

    @patch("crumbs.cli.GitRepository")
    def test_quality_verbose_shows_non_conventional(
        self, mock_repo_class, runner, mock_repository
    ):
        """Quality verbose shows non-conventional commits."""
        mock_repo_class.return_value = mock_repository

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            (repo_path / ".git").mkdir()

            result = runner.invoke(cli, ["quality", str(repo_path), "-v"])

            assert result.exit_code == 0
            # We have one non-conventional commit in mock_commits
            assert "Non-conventional commits" in result.output
            assert "quick fix" in result.output

    @patch("crumbs.cli.GitRepository")
    def test_quality_no_commits(self, mock_repo_class, runner):
        """Quality handles repository with no commits."""
        mock_repo = MagicMock()
        mock_repo.name = "empty-repo"
        mock_repo.iter_commits.return_value = iter([])
        mock_repo_class.return_value = mock_repo

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            (repo_path / ".git").mkdir()

            result = runner.invoke(cli, ["quality", str(repo_path)])

            assert result.exit_code == 0
            assert "No commits found" in result.output


class TestDateFiltering:
    """Tests for date filtering options."""

    @patch("crumbs.cli.GitRepository")
    def test_since_and_until(self, mock_repo_class, runner, mock_repository):
        """Commands handle both since and until filters."""
        mock_repo_class.return_value = mock_repository

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            (repo_path / ".git").mkdir()

            result = runner.invoke(
                cli,
                [
                    "stats",
                    str(repo_path),
                    "--since",
                    "2024-01-01",
                    "--until",
                    "2024-12-31",
                ],
            )

            assert result.exit_code == 0
            call_kwargs = mock_repository.iter_commits.call_args[1]
            assert call_kwargs["since"] == datetime(2024, 1, 1, tzinfo=timezone.utc)
            assert call_kwargs["until"] == datetime(2024, 12, 31, tzinfo=timezone.utc)


class TestErrorHandling:
    """Tests for CLI error handling."""

    @patch("crumbs.cli.GitRepository")
    def test_git_repository_error(self, mock_repo_class, runner):
        """CLI handles GitRepositoryError gracefully."""
        from crumbs.git.repository import GitRepositoryError

        mock_repo_class.side_effect = GitRepositoryError("Not a git repository")

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            (repo_path / ".git").mkdir()

            result = runner.invoke(cli, ["stats", str(repo_path)])

            assert result.exit_code == 1
            assert "Error" in result.output
            assert "Not a git repository" in result.output

    def test_invalid_date_format(self, runner):
        """CLI handles invalid date format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            (repo_path / ".git").mkdir()

            result = runner.invoke(
                cli, ["stats", str(repo_path), "--since", "not-a-date"]
            )

            assert result.exit_code != 0
