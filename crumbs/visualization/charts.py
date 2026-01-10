"""Plotly chart generators."""

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from crumbs.models import RepositoryStats, CommitType, SentimentResult


class ChartGenerator:
    """Generate Plotly charts from repository statistics.

    All chart methods return Plotly Figure objects that can be
    rendered to HTML, PNG, or displayed interactively.
    """

    # Color palette for charts
    COLORS = {
        "primary": "#2563eb",
        "secondary": "#7c3aed",
        "success": "#16a34a",
        "danger": "#dc2626",
        "warning": "#d97706",
        "info": "#0891b2",
    }

    # Colors for commit types
    TYPE_COLORS = {
        CommitType.FEAT: "#2563eb",
        CommitType.FIX: "#dc2626",
        CommitType.DOCS: "#7c3aed",
        CommitType.STYLE: "#ec4899",
        CommitType.REFACTOR: "#f59e0b",
        CommitType.PERF: "#10b981",
        CommitType.TEST: "#06b6d4",
        CommitType.BUILD: "#6366f1",
        CommitType.CI: "#8b5cf6",
        CommitType.CHORE: "#6b7280",
        CommitType.REVERT: "#ef4444",
        CommitType.UNKNOWN: "#9ca3af",
    }

    # Colors for sentiment
    SENTIMENT_COLORS = {
        "positive": "#22c55e",
        "neutral": "#94a3b8",
        "negative": "#ef4444",
    }

    def __init__(self, stats: RepositoryStats):
        """Initialize the chart generator.

        Args:
            stats: RepositoryStats object with aggregated metrics
        """
        self.stats = stats

    def velocity_chart(self) -> go.Figure:
        """Generate commits over time chart.

        Returns:
            Plotly Figure showing daily commit counts as a bar chart
        """
        if not self.stats.commits_by_day:
            return self._empty_figure("No commit data available")

        # Sort days chronologically
        sorted_days = sorted(self.stats.commits_by_day.keys())
        counts = [self.stats.commits_by_day[day] for day in sorted_days]

        fig = go.Figure(
            data=[
                go.Bar(
                    x=sorted_days,
                    y=counts,
                    marker_color=self.COLORS["primary"],
                    hovertemplate="%{x}<br>%{y} commits<extra></extra>",
                )
            ]
        )

        fig.update_layout(
            title="Commit Velocity",
            xaxis_title="Date",
            yaxis_title="Commits",
            template="plotly_white",
            hovermode="x unified",
        )

        return fig

    def commit_size_histogram(self) -> go.Figure:
        """Generate size distribution histogram.

        Returns:
            Plotly Figure showing commit size distribution
        """
        if not self.stats.size_distribution:
            return self._empty_figure("No size data available")

        # Define order for size buckets
        bucket_order = ["small", "medium", "large", "xlarge"]
        bucket_labels = {
            "small": "Small (1-10)",
            "medium": "Medium (11-50)",
            "large": "Large (51-200)",
            "xlarge": "XLarge (200+)",
        }
        bucket_colors = {
            "small": "#22c55e",
            "medium": "#3b82f6",
            "large": "#f59e0b",
            "xlarge": "#ef4444",
        }

        labels = []
        values = []
        colors = []

        for bucket in bucket_order:
            if bucket in self.stats.size_distribution:
                labels.append(bucket_labels[bucket])
                values.append(self.stats.size_distribution[bucket])
                colors.append(bucket_colors[bucket])

        fig = go.Figure(
            data=[
                go.Bar(
                    x=labels,
                    y=values,
                    marker_color=colors,
                    hovertemplate="%{x}<br>%{y} commits<extra></extra>",
                )
            ]
        )

        fig.update_layout(
            title="Commit Size Distribution",
            xaxis_title="Size Category",
            yaxis_title="Number of Commits",
            template="plotly_white",
        )

        return fig

    def phase_burndown(self) -> go.Figure:
        """Generate phase completion chart.

        Returns:
            Plotly Figure showing commits per phase as a bar chart
        """
        if not self.stats.commits_by_phase:
            return self._empty_figure("No phase data available")

        # Sort phases numerically
        sorted_phases = sorted(self.stats.commits_by_phase.keys())
        phase_labels = [f"Phase {p}" for p in sorted_phases]
        counts = [self.stats.commits_by_phase[p] for p in sorted_phases]

        fig = go.Figure(
            data=[
                go.Bar(
                    x=phase_labels,
                    y=counts,
                    marker_color=self.COLORS["secondary"],
                    hovertemplate="%{x}<br>%{y} commits<extra></extra>",
                )
            ]
        )

        fig.update_layout(
            title="Commits by Phase",
            xaxis_title="Phase",
            yaxis_title="Commits",
            template="plotly_white",
        )

        return fig

    def code_churn_chart(self) -> go.Figure:
        """Generate additions vs deletions chart.

        Returns:
            Plotly Figure showing code churn as grouped bars
        """
        fig = go.Figure(
            data=[
                go.Bar(
                    name="Lines Added",
                    x=["Code Changes"],
                    y=[self.stats.total_lines_added],
                    marker_color=self.COLORS["success"],
                ),
                go.Bar(
                    name="Lines Deleted",
                    x=["Code Changes"],
                    y=[self.stats.total_lines_deleted],
                    marker_color=self.COLORS["danger"],
                ),
            ]
        )

        fig.update_layout(
            title="Code Churn",
            yaxis_title="Lines",
            template="plotly_white",
            barmode="group",
            showlegend=True,
        )

        # Add annotation for net change
        net_change = self.stats.total_lines_added - self.stats.total_lines_deleted
        sign = "+" if net_change >= 0 else ""
        fig.add_annotation(
            text=f"Net: {sign}{net_change:,} lines",
            xref="paper",
            yref="paper",
            x=0.5,
            y=1.05,
            showarrow=False,
            font=dict(size=12),
        )

        return fig

    def hourly_heatmap(self) -> go.Figure:
        """Generate activity by hour heatmap.

        Returns:
            Plotly Figure showing commit activity by hour of day
        """
        # Create full 24-hour range
        hours = list(range(24))
        counts = [self.stats.commits_by_hour.get(h, 0) for h in hours]

        # Format hours as AM/PM
        hour_labels = []
        for h in hours:
            if h == 0:
                hour_labels.append("12 AM")
            elif h < 12:
                hour_labels.append(f"{h} AM")
            elif h == 12:
                hour_labels.append("12 PM")
            else:
                hour_labels.append(f"{h - 12} PM")

        fig = go.Figure(
            data=[
                go.Bar(
                    x=hour_labels,
                    y=counts,
                    marker=dict(
                        color=counts,
                        colorscale="Blues",
                        showscale=True,
                        colorbar=dict(title="Commits"),
                    ),
                    hovertemplate="%{x}<br>%{y} commits<extra></extra>",
                )
            ]
        )

        fig.update_layout(
            title="Commit Activity by Hour",
            xaxis_title="Hour of Day",
            yaxis_title="Commits",
            template="plotly_white",
            xaxis=dict(tickangle=-45),
        )

        return fig

    def type_distribution(self) -> go.Figure:
        """Generate pie chart of commit types.

        Returns:
            Plotly Figure showing distribution of commit types
        """
        if not self.stats.commits_by_type:
            return self._empty_figure("No commit type data available")

        labels = []
        values = []
        colors = []

        for commit_type, count in sorted(
            self.stats.commits_by_type.items(),
            key=lambda x: x[1],
            reverse=True,
        ):
            labels.append(commit_type.value)
            values.append(count)
            colors.append(self.TYPE_COLORS.get(commit_type, "#9ca3af"))

        fig = go.Figure(
            data=[
                go.Pie(
                    labels=labels,
                    values=values,
                    marker=dict(colors=colors),
                    textinfo="label+percent",
                    hovertemplate="%{label}<br>%{value} commits (%{percent})<extra></extra>",
                )
            ]
        )

        fig.update_layout(
            title="Commit Types Distribution",
            template="plotly_white",
            showlegend=True,
        )

        return fig

    def author_distribution(self) -> go.Figure:
        """Generate bar chart of commits by author.

        Returns:
            Plotly Figure showing commits per author
        """
        if not self.stats.commits_by_author:
            return self._empty_figure("No author data available")

        # Sort by commit count
        sorted_authors = sorted(
            self.stats.commits_by_author.items(),
            key=lambda x: x[1],
            reverse=True,
        )

        authors = [a[0] for a in sorted_authors]
        counts = [a[1] for a in sorted_authors]

        fig = go.Figure(
            data=[
                go.Bar(
                    x=authors,
                    y=counts,
                    marker_color=self.COLORS["info"],
                    hovertemplate="%{x}<br>%{y} commits<extra></extra>",
                )
            ]
        )

        fig.update_layout(
            title="Commits by Author",
            xaxis_title="Author",
            yaxis_title="Commits",
            template="plotly_white",
            xaxis=dict(tickangle=-45),
        )

        return fig

    def sentiment_chart(
        self, sentiment_results: list[SentimentResult]
    ) -> go.Figure:
        """Generate sentiment distribution chart.

        Creates a combined visualization with:
        - Donut chart showing positive/neutral/negative distribution
        - Bar chart showing tone breakdown

        Args:
            sentiment_results: List of SentimentResult objects from LLM analysis

        Returns:
            Plotly Figure showing sentiment analysis
        """
        if not sentiment_results:
            return self._empty_figure("No sentiment data available")

        # Count sentiments
        sentiment_counts = {"positive": 0, "neutral": 0, "negative": 0}
        tone_counts: dict[str, int] = {}

        for result in sentiment_results:
            sentiment = result.sentiment.lower()
            if sentiment in sentiment_counts:
                sentiment_counts[sentiment] += 1
            else:
                sentiment_counts["neutral"] += 1

            # Count tones
            tone = result.tone.lower()
            tone_counts[tone] = tone_counts.get(tone, 0) + 1

        # Create subplot with donut chart and tone bar chart
        fig = make_subplots(
            rows=1,
            cols=2,
            specs=[[{"type": "pie"}, {"type": "bar"}]],
            subplot_titles=("Sentiment Distribution", "Tone Breakdown"),
        )

        # Donut chart for sentiment
        labels = list(sentiment_counts.keys())
        values = list(sentiment_counts.values())
        colors = [self.SENTIMENT_COLORS.get(s, "#94a3b8") for s in labels]

        fig.add_trace(
            go.Pie(
                labels=[s.capitalize() for s in labels],
                values=values,
                marker=dict(colors=colors),
                hole=0.4,
                textinfo="label+percent",
                hovertemplate="%{label}<br>%{value} commits (%{percent})<extra></extra>",
            ),
            row=1,
            col=1,
        )

        # Bar chart for tones (top 8)
        sorted_tones = sorted(tone_counts.items(), key=lambda x: x[1], reverse=True)[:8]
        if sorted_tones:
            tone_labels = [t[0].capitalize() for t in sorted_tones]
            tone_values = [t[1] for t in sorted_tones]

            fig.add_trace(
                go.Bar(
                    x=tone_labels,
                    y=tone_values,
                    marker_color=self.COLORS["info"],
                    hovertemplate="%{x}<br>%{y} commits<extra></extra>",
                ),
                row=1,
                col=2,
            )

        fig.update_layout(
            title="Commit Sentiment Analysis",
            template="plotly_white",
            showlegend=False,
        )

        return fig

    def sentiment_pie(self, sentiment_results: list[SentimentResult]) -> go.Figure:
        """Generate simple sentiment pie chart.

        Args:
            sentiment_results: List of SentimentResult objects

        Returns:
            Plotly Figure with sentiment pie chart
        """
        if not sentiment_results:
            return self._empty_figure("No sentiment data available")

        sentiment_counts = {"positive": 0, "neutral": 0, "negative": 0}
        for result in sentiment_results:
            sentiment = result.sentiment.lower()
            if sentiment in sentiment_counts:
                sentiment_counts[sentiment] += 1

        labels = [s.capitalize() for s in sentiment_counts.keys()]
        values = list(sentiment_counts.values())
        colors = [self.SENTIMENT_COLORS.get(s.lower(), "#94a3b8") for s in sentiment_counts.keys()]

        fig = go.Figure(
            data=[
                go.Pie(
                    labels=labels,
                    values=values,
                    marker=dict(colors=colors),
                    hole=0.4,
                    textinfo="label+percent",
                    hovertemplate="%{label}<br>%{value} commits (%{percent})<extra></extra>",
                )
            ]
        )

        fig.update_layout(
            title="Sentiment Distribution",
            template="plotly_white",
        )

        return fig

    def all_charts(self) -> list[go.Figure]:
        """Generate all available charts.

        Returns:
            List of Plotly Figure objects
        """
        charts = [
            self.velocity_chart(),
            self.type_distribution(),
            self.commit_size_histogram(),
            self.code_churn_chart(),
            self.hourly_heatmap(),
        ]

        # Only include phase chart if phases are detected
        if self.stats.phases_detected:
            charts.append(self.phase_burndown())

        # Only include author chart if multiple authors
        if len(self.stats.commits_by_author) > 1:
            charts.append(self.author_distribution())

        return charts

    def _empty_figure(self, message: str) -> go.Figure:
        """Create an empty figure with a message.

        Args:
            message: Message to display

        Returns:
            Empty Plotly Figure with centered message
        """
        fig = go.Figure()
        fig.add_annotation(
            text=message,
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=16, color="#6b7280"),
        )
        fig.update_layout(
            template="plotly_white",
            xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
            yaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        )
        return fig
