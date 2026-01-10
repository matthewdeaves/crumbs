"""Tests for GitRepository class."""

import os
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from crumbs.git import GitRepository, GitRepositoryError
from crumbs.models import CommitType


@pytest.fixture
def temp_git_repo(tmp_path):
    """Create a temporary git repository with sample commits."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()

    # Initialize git repo
    subprocess.run(["git", "init"], cwd=repo_path, capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo_path,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test Author"],
        cwd=repo_path,
        capture_output=True,
        check=True,
    )

    # Create initial commit
    readme = repo_path / "README.md"
    readme.write_text("# Test Repository\n")
    subprocess.run(["git", "add", "."], cwd=repo_path, capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "chore: initial commit\n\nPhase 1 setup"],
        cwd=repo_path,
        capture_output=True,
        check=True,
    )

    # Create a conventional commit with scope
    main_py = repo_path / "main.py"
    main_py.write_text("def main():\n    print('Hello')\n")
    subprocess.run(["git", "add", "."], cwd=repo_path, capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "feat(core): add main function"],
        cwd=repo_path,
        capture_output=True,
        check=True,
    )

    # Create a commit with co-author
    main_py.write_text("def main():\n    print('Hello, World!')\n")
    subprocess.run(["git", "add", "."], cwd=repo_path, capture_output=True, check=True)
    subprocess.run(
        [
            "git",
            "commit",
            "-m",
            "fix(core): update greeting\n\nCo-Authored-By: Claude <claude@anthropic.com>",
        ],
        cwd=repo_path,
        capture_output=True,
        check=True,
    )

    # Create a non-conventional commit
    utils_py = repo_path / "utils.py"
    utils_py.write_text("def helper():\n    pass\n")
    subprocess.run(["git", "add", "."], cwd=repo_path, capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "added helper function"],
        cwd=repo_path,
        capture_output=True,
        check=True,
    )

    return repo_path


@pytest.fixture
def git_repo(temp_git_repo):
    """Create a GitRepository instance from temp repo."""
    return GitRepository(str(temp_git_repo))


class TestGitRepositoryInit:
    """Tests for GitRepository initialization."""

    def test_valid_repository(self, temp_git_repo):
        """Can initialize with valid git repository."""
        repo = GitRepository(str(temp_git_repo))
        assert repo.path == temp_git_repo

    def test_invalid_repository(self, tmp_path):
        """Raises error for non-git directory."""
        with pytest.raises(GitRepositoryError) as exc_info:
            GitRepository(str(tmp_path))

        assert "Not a git repository" in str(exc_info.value)

    def test_repository_name(self, git_repo, temp_git_repo):
        """Repository name is derived from directory."""
        assert git_repo.name == temp_git_repo.name


class TestIterCommits:
    """Tests for iter_commits method."""

    def test_iter_all_commits(self, git_repo):
        """Can iterate over all commits."""
        commits = list(git_repo.iter_commits())

        assert len(commits) == 4

    def test_commits_are_in_order(self, git_repo):
        """Commits are returned newest first."""
        commits = list(git_repo.iter_commits())

        # Most recent commit is first (non-conventional one)
        assert commits[0].message.startswith("added helper")
        # Oldest commit is last
        assert "initial commit" in commits[-1].message

    def test_commit_has_sha(self, git_repo):
        """Each commit has a SHA."""
        commits = list(git_repo.iter_commits())

        for commit in commits:
            assert commit.sha
            assert len(commit.sha) == 40  # Full SHA

    def test_commit_has_author(self, git_repo):
        """Each commit has author info."""
        commits = list(git_repo.iter_commits())

        for commit in commits:
            assert commit.author == "Test Author"
            assert commit.author_email == "test@example.com"

    def test_commit_has_timestamp(self, git_repo):
        """Each commit has a UTC timestamp."""
        commits = list(git_repo.iter_commits())

        for commit in commits:
            assert commit.timestamp is not None
            assert commit.timestamp.tzinfo == timezone.utc


class TestCommitParsing:
    """Tests for commit message parsing during iteration."""

    def test_conventional_commit_parsed(self, git_repo):
        """Conventional commits are properly parsed."""
        commits = list(git_repo.iter_commits())

        # Find the feat(core) commit
        feat_commit = next(c for c in commits if c.scope == "core" and c.commit_type == CommitType.FEAT)

        assert feat_commit.commit_type == CommitType.FEAT
        assert feat_commit.scope == "core"
        assert feat_commit.subject == "add main function"
        assert feat_commit.is_conventional is True

    def test_non_conventional_commit(self, git_repo):
        """Non-conventional commits have UNKNOWN type."""
        commits = list(git_repo.iter_commits())

        # Find the non-conventional commit
        non_conv = next(c for c in commits if "helper" in c.message)

        assert non_conv.commit_type == CommitType.UNKNOWN
        assert non_conv.is_conventional is False

    def test_co_author_extracted(self, git_repo):
        """Co-authors are extracted from commits."""
        commits = list(git_repo.iter_commits())

        # Find the commit with co-author
        co_authored = next(c for c in commits if c.co_authors)

        assert len(co_authored.co_authors) == 1
        assert "Claude" in co_authored.co_authors[0]

    def test_phase_detected(self, git_repo):
        """Phase is detected from commit message."""
        commits = list(git_repo.iter_commits())

        # Find the commit with phase
        phase_commit = next(c for c in commits if c.phase is not None)

        assert phase_commit.phase == 1


class TestCommitStats:
    """Tests for commit statistics."""

    def test_commit_has_stats(self, git_repo):
        """Each commit has stats object."""
        commits = list(git_repo.iter_commits())

        for commit in commits:
            assert commit.stats is not None

    def test_stats_have_values(self, git_repo):
        """Stats contain meaningful values for non-initial commits."""
        commits = list(git_repo.iter_commits())

        # Get a non-initial commit (should have some changes)
        non_initial = [c for c in commits if "initial" not in c.message]

        # At least some commits should have changes
        has_changes = any(c.stats.total_changes > 0 for c in non_initial)
        assert has_changes

    def test_files_changed_tracked(self, git_repo):
        """Files changed is tracked in stats."""
        commits = list(git_repo.iter_commits())

        # Find commit that added utils.py
        utils_commit = next(c for c in commits if "helper" in c.message)

        assert utils_commit.stats.files_changed >= 1


class TestCommitFilters:
    """Tests for commit filtering."""

    def test_filter_by_author(self, git_repo):
        """Can filter commits by author."""
        commits = list(git_repo.iter_commits(author="Test Author"))

        assert len(commits) == 4  # All commits are by Test Author

    def test_filter_by_nonexistent_author(self, git_repo):
        """Filtering by non-existent author returns empty."""
        commits = list(git_repo.iter_commits(author="Nobody"))

        assert len(commits) == 0


class TestRepositoryProperties:
    """Tests for repository properties."""

    def test_head_commit(self, git_repo):
        """Can get HEAD commit."""
        head = git_repo.head_commit

        assert head is not None
        assert "helper" in head.message  # Most recent commit

    def test_branches(self, git_repo):
        """Can get branch list."""
        branches = git_repo.branches

        assert len(branches) >= 1
        # Default branch could be 'main' or 'master'
        assert any(b in ["main", "master"] for b in branches)

    def test_active_branch(self, git_repo):
        """Can get active branch."""
        branch = git_repo.active_branch

        assert branch in ["main", "master"]


class TestGetCommit:
    """Tests for getting specific commits."""

    def test_get_commit_by_sha(self, git_repo):
        """Can get commit by full SHA."""
        commits = list(git_repo.iter_commits())
        first = commits[0]

        retrieved = git_repo.get_commit(first.sha)

        assert retrieved is not None
        assert retrieved.sha == first.sha

    def test_get_commit_by_short_sha(self, git_repo):
        """Can get commit by short SHA."""
        commits = list(git_repo.iter_commits())
        first = commits[0]

        retrieved = git_repo.get_commit(first.sha[:7])

        assert retrieved is not None
        assert retrieved.sha == first.sha

    def test_get_nonexistent_commit(self, git_repo):
        """Getting non-existent commit returns None."""
        result = git_repo.get_commit("0000000000000000000000000000000000000000")

        assert result is None
