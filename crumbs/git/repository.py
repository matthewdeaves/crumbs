"""GitPython wrapper for repository operations."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Optional

from git import Repo
from git.exc import InvalidGitRepositoryError, GitCommandError

from crumbs.models import Commit, CommitStats, CommitType
from crumbs.git.parser import CommitMessageParser


class GitRepositoryError(Exception):
    """Exception raised for git repository errors."""

    pass


class GitRepository:
    """Wrapper around GitPython for repository operations.

    Provides a clean interface for iterating over commits and
    extracting commit statistics.
    """

    def __init__(self, path: str):
        """Initialize the repository wrapper.

        Args:
            path: Path to the git repository

        Raises:
            GitRepositoryError: If path is not a valid git repository
        """
        self.path = Path(path)
        self._parser = CommitMessageParser()

        try:
            self._repo = Repo(self.path)
        except InvalidGitRepositoryError:
            raise GitRepositoryError(f"Not a git repository: {path}")

    @property
    def name(self) -> str:
        """Get the repository name from the directory."""
        return self.path.name

    def iter_commits(
        self,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        author: Optional[str] = None,
        branch: Optional[str] = None,
    ) -> Iterator[Commit]:
        """Iterate over commits in the repository.

        Args:
            since: Only include commits after this date
            until: Only include commits before this date
            author: Filter by author name or email
            branch: Branch to iterate (default: current branch)

        Yields:
            Commit objects with parsed data
        """
        # Build kwargs for git log
        kwargs = {}

        if since:
            kwargs["since"] = since.isoformat()
        if until:
            kwargs["until"] = until.isoformat()
        if author:
            kwargs["author"] = author

        # Get the revision to iterate
        rev = branch if branch else None

        try:
            for git_commit in self._repo.iter_commits(rev=rev, **kwargs):
                yield self._convert_commit(git_commit)
        except GitCommandError as e:
            raise GitRepositoryError(f"Git command failed: {e}")

    def _convert_commit(self, git_commit) -> Commit:
        """Convert a GitPython commit to our Commit model.

        Args:
            git_commit: GitPython Commit object

        Returns:
            Our Commit dataclass
        """
        message = git_commit.message

        # Parse the commit message
        parsed = self._parser.parse(message)

        # Extract co-authors
        co_authors = self._parser.extract_co_authors(message)

        # Detect phase
        phase = self._parser.detect_phase(message)

        # Get commit stats
        stats = self.get_commit_stats(git_commit)

        # Convert timestamp to UTC datetime
        timestamp = datetime.fromtimestamp(
            git_commit.committed_date, tz=timezone.utc
        )

        return Commit(
            sha=git_commit.hexsha,
            message=message,
            author=git_commit.author.name,
            author_email=git_commit.author.email,
            timestamp=timestamp,
            stats=stats,
            commit_type=parsed.commit_type,
            scope=parsed.scope,
            subject=parsed.subject,
            body=parsed.body,
            co_authors=co_authors,
            phase=phase,
            is_conventional=parsed.is_conventional,
        )

    def get_commit_stats(self, git_commit) -> CommitStats:
        """Get diff statistics for a commit.

        Args:
            git_commit: GitPython Commit object

        Returns:
            CommitStats with lines added/deleted and files changed
        """
        try:
            # For the initial commit, there's no parent
            if not git_commit.parents:
                # Compare with empty tree
                diff = git_commit.diff(
                    None,  # Compare with nothing (empty tree)
                    create_patch=True,
                )
                lines_added = 0
                lines_deleted = 0
                files_changed = len(diff)

                for d in diff:
                    # For new files, count all lines as added
                    if d.b_blob:
                        try:
                            content = d.b_blob.data_stream.read().decode(
                                "utf-8", errors="replace"
                            )
                            lines_added += len(content.splitlines())
                        except Exception:
                            pass

                return CommitStats(
                    lines_added=lines_added,
                    lines_deleted=lines_deleted,
                    files_changed=files_changed,
                )

            # Get stats from diff with parent
            parent = git_commit.parents[0]
            stats = git_commit.stats

            return CommitStats(
                lines_added=stats.total.get("insertions", 0),
                lines_deleted=stats.total.get("deletions", 0),
                files_changed=stats.total.get("files", 0),
            )

        except Exception:
            # Return empty stats on any error
            return CommitStats()

    def get_commit(self, sha: str) -> Optional[Commit]:
        """Get a specific commit by SHA.

        Args:
            sha: Full or abbreviated commit SHA

        Returns:
            Commit object or None if not found
        """
        try:
            git_commit = self._repo.commit(sha)
            return self._convert_commit(git_commit)
        except Exception:
            return None

    @property
    def head_commit(self) -> Optional[Commit]:
        """Get the HEAD commit."""
        try:
            return self._convert_commit(self._repo.head.commit)
        except Exception:
            return None

    @property
    def branches(self) -> list[str]:
        """Get list of branch names."""
        return [branch.name for branch in self._repo.branches]

    @property
    def active_branch(self) -> Optional[str]:
        """Get the current active branch name."""
        try:
            return self._repo.active_branch.name
        except TypeError:
            # Detached HEAD state
            return None
