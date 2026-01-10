"""Statistical calculations for commits."""

from collections import defaultdict
from datetime import datetime, timedelta

from crumbs.models import Commit, RepositoryStats


class StatsCalculator:
    """Calculate statistics from commits.

    Takes a list of Commit objects and computes various aggregate
    statistics including temporal patterns, size distributions,
    and work session detection.
    """

    # Gap between commits that defines a new work session (hours)
    SESSION_GAP_HOURS = 2.0

    def __init__(self, commits: list[Commit]):
        """Initialize the calculator with commits.

        Args:
            commits: List of Commit objects to analyze
        """
        self.commits = list(commits)
        self._stats: RepositoryStats | None = None

    def calculate(self) -> RepositoryStats:
        """Calculate all repository statistics.

        Returns:
            RepositoryStats with aggregated metrics
        """
        if self._stats is not None:
            return self._stats

        if not self.commits:
            self._stats = RepositoryStats()
            return self._stats

        # Sort commits by timestamp for temporal analysis
        sorted_commits = sorted(self.commits, key=lambda c: c.timestamp)

        # Initialize counters
        commits_by_type = defaultdict(int)
        commits_by_author = defaultdict(int)
        commits_by_day = defaultdict(int)
        commits_by_hour = defaultdict(int)
        commits_by_phase = defaultdict(int)
        size_distribution = defaultdict(int)

        total_lines_added = 0
        total_lines_deleted = 0
        total_files_changed = 0
        conventional_count = 0
        co_authored_count = 0
        phases_detected = set()

        for commit in sorted_commits:
            # Count by type
            commits_by_type[commit.commit_type] += 1

            # Count by author
            commits_by_author[commit.author] += 1

            # Count by day (YYYY-MM-DD format)
            day_key = commit.timestamp.strftime("%Y-%m-%d")
            commits_by_day[day_key] += 1

            # Count by hour
            commits_by_hour[commit.timestamp.hour] += 1

            # Count by phase
            if commit.phase is not None:
                commits_by_phase[commit.phase] += 1
                phases_detected.add(commit.phase)

            # Size distribution
            size_distribution[commit.stats.size_bucket] += 1

            # Totals
            total_lines_added += commit.stats.lines_added
            total_lines_deleted += commit.stats.lines_deleted
            total_files_changed += commit.stats.files_changed

            # Conventional commit count
            if commit.is_conventional:
                conventional_count += 1

            # Co-authored count
            if commit.co_authors:
                co_authored_count += 1

        # Calculate average commit interval
        avg_interval = self._calculate_avg_interval(sorted_commits)

        # Detect work sessions
        work_sessions = self._detect_work_sessions(sorted_commits)

        self._stats = RepositoryStats(
            total_commits=len(sorted_commits),
            total_lines_added=total_lines_added,
            total_lines_deleted=total_lines_deleted,
            total_files_changed=total_files_changed,
            commits_by_type=dict(commits_by_type),
            commits_by_author=dict(commits_by_author),
            commits_by_day=dict(commits_by_day),
            commits_by_hour=dict(commits_by_hour),
            commits_by_phase=dict(commits_by_phase),
            size_distribution=dict(size_distribution),
            conventional_count=conventional_count,
            co_authored_count=co_authored_count,
            phases_detected=sorted(phases_detected),
            first_commit_date=sorted_commits[0].timestamp,
            last_commit_date=sorted_commits[-1].timestamp,
            avg_commit_interval_hours=avg_interval,
            work_sessions=work_sessions,
        )

        return self._stats

    def _calculate_avg_interval(self, sorted_commits: list[Commit]) -> float:
        """Calculate average time between commits in hours.

        Args:
            sorted_commits: Commits sorted by timestamp

        Returns:
            Average interval in hours, or 0.0 if < 2 commits
        """
        if len(sorted_commits) < 2:
            return 0.0

        total_seconds = 0.0
        for i in range(1, len(sorted_commits)):
            delta = sorted_commits[i].timestamp - sorted_commits[i - 1].timestamp
            total_seconds += delta.total_seconds()

        avg_seconds = total_seconds / (len(sorted_commits) - 1)
        return avg_seconds / 3600.0  # Convert to hours

    def _detect_work_sessions(self, sorted_commits: list[Commit]) -> int:
        """Detect number of work sessions based on commit gaps.

        A new session starts when the gap between commits exceeds
        SESSION_GAP_HOURS.

        Args:
            sorted_commits: Commits sorted by timestamp

        Returns:
            Number of detected work sessions
        """
        if not sorted_commits:
            return 0

        sessions = 1
        gap_threshold = timedelta(hours=self.SESSION_GAP_HOURS)

        for i in range(1, len(sorted_commits)):
            delta = sorted_commits[i].timestamp - sorted_commits[i - 1].timestamp
            if delta > gap_threshold:
                sessions += 1

        return sessions

    @property
    def total_commits(self) -> int:
        """Total number of commits."""
        return self.calculate().total_commits

    @property
    def conventional_compliance(self) -> float:
        """Percentage of commits following conventional format."""
        return self.calculate().conventional_compliance

    @property
    def co_authored_percentage(self) -> float:
        """Percentage of commits with co-authors."""
        return self.calculate().co_authored_percentage

    @property
    def stats(self) -> RepositoryStats:
        """Get the calculated repository stats."""
        return self.calculate()
