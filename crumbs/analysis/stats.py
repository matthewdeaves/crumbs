"""Statistical calculations for commits."""


class StatsCalculator:
    """Calculate statistics from commits."""

    def __init__(self, commits):
        self.commits = commits

    @property
    def total_commits(self):
        raise NotImplementedError("Will be implemented in Session 3")

    @property
    def conventional_compliance(self):
        raise NotImplementedError("Will be implemented in Session 3")
