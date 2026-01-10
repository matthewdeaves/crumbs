"""Plotly chart generators."""


class ChartGenerator:
    """Generate Plotly charts from stats."""

    def __init__(self, stats):
        self.stats = stats

    def velocity_chart(self):
        """Generate commits over time chart."""
        raise NotImplementedError("Will be implemented in Session 4")

    def commit_size_histogram(self):
        """Generate size distribution histogram."""
        raise NotImplementedError("Will be implemented in Session 4")

    def phase_burndown(self):
        """Generate phase completion over time chart."""
        raise NotImplementedError("Will be implemented in Session 4")

    def code_churn_chart(self):
        """Generate additions vs deletions chart."""
        raise NotImplementedError("Will be implemented in Session 4")

    def hourly_heatmap(self):
        """Generate activity by hour heatmap."""
        raise NotImplementedError("Will be implemented in Session 4")

    def type_distribution(self):
        """Generate pie chart of commit types."""
        raise NotImplementedError("Will be implemented in Session 4")
