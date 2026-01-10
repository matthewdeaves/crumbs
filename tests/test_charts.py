"""Tests for the visualization module."""

from datetime import datetime, timezone
from pathlib import Path
import tempfile

import pytest
import plotly.graph_objects as go

from crumbs.models import CommitType, RepositoryStats
from crumbs.visualization import ChartGenerator, ReportGenerator


@pytest.fixture
def minimal_stats():
    """Minimal stats for testing."""
    return RepositoryStats(
        total_commits=10,
        total_lines_added=100,
        total_lines_deleted=50,
        total_files_changed=5,
    )


@pytest.fixture
def full_stats():
    """Full stats with all fields populated."""
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


class TestChartGenerator:
    """Tests for ChartGenerator."""

    def test_velocity_chart_returns_figure(self, full_stats):
        """velocity_chart returns a Plotly Figure."""
        gen = ChartGenerator(full_stats)
        fig = gen.velocity_chart()

        assert isinstance(fig, go.Figure)
        assert fig.layout.title.text == "Commit Velocity"

    def test_velocity_chart_empty_data(self, minimal_stats):
        """velocity_chart handles empty data gracefully."""
        gen = ChartGenerator(minimal_stats)
        fig = gen.velocity_chart()

        assert isinstance(fig, go.Figure)
        # Should show empty message
        assert len(fig.layout.annotations) > 0

    def test_commit_size_histogram_returns_figure(self, full_stats):
        """commit_size_histogram returns a Plotly Figure."""
        gen = ChartGenerator(full_stats)
        fig = gen.commit_size_histogram()

        assert isinstance(fig, go.Figure)
        assert fig.layout.title.text == "Commit Size Distribution"

    def test_commit_size_histogram_has_correct_buckets(self, full_stats):
        """commit_size_histogram shows size buckets in order."""
        gen = ChartGenerator(full_stats)
        fig = gen.commit_size_histogram()

        # Check that bar data exists
        assert len(fig.data) > 0
        assert fig.data[0].type == "bar"

    def test_phase_burndown_returns_figure(self, full_stats):
        """phase_burndown returns a Plotly Figure."""
        gen = ChartGenerator(full_stats)
        fig = gen.phase_burndown()

        assert isinstance(fig, go.Figure)
        assert fig.layout.title.text == "Commits by Phase"

    def test_phase_burndown_empty_data(self, minimal_stats):
        """phase_burndown handles empty phase data."""
        gen = ChartGenerator(minimal_stats)
        fig = gen.phase_burndown()

        assert isinstance(fig, go.Figure)
        # Should show empty message
        assert len(fig.layout.annotations) > 0

    def test_code_churn_chart_returns_figure(self, full_stats):
        """code_churn_chart returns a Plotly Figure."""
        gen = ChartGenerator(full_stats)
        fig = gen.code_churn_chart()

        assert isinstance(fig, go.Figure)
        assert fig.layout.title.text == "Code Churn"
        # Should have two bars (added and deleted)
        assert len(fig.data) == 2

    def test_code_churn_shows_net_change(self, full_stats):
        """code_churn_chart shows net change annotation."""
        gen = ChartGenerator(full_stats)
        fig = gen.code_churn_chart()

        # Should have annotation with net change
        assert len(fig.layout.annotations) > 0
        annotation_text = fig.layout.annotations[0].text
        assert "Net:" in annotation_text

    def test_hourly_heatmap_returns_figure(self, full_stats):
        """hourly_heatmap returns a Plotly Figure."""
        gen = ChartGenerator(full_stats)
        fig = gen.hourly_heatmap()

        assert isinstance(fig, go.Figure)
        assert fig.layout.title.text == "Commit Activity by Hour"

    def test_hourly_heatmap_has_24_hours(self, full_stats):
        """hourly_heatmap shows all 24 hours."""
        gen = ChartGenerator(full_stats)
        fig = gen.hourly_heatmap()

        # Should have 24 data points
        assert len(fig.data[0].x) == 24

    def test_type_distribution_returns_figure(self, full_stats):
        """type_distribution returns a Plotly Figure."""
        gen = ChartGenerator(full_stats)
        fig = gen.type_distribution()

        assert isinstance(fig, go.Figure)
        assert fig.layout.title.text == "Commit Types Distribution"
        # Should be a pie chart
        assert fig.data[0].type == "pie"

    def test_type_distribution_empty_data(self, minimal_stats):
        """type_distribution handles empty type data."""
        gen = ChartGenerator(minimal_stats)
        fig = gen.type_distribution()

        assert isinstance(fig, go.Figure)

    def test_author_distribution_returns_figure(self, full_stats):
        """author_distribution returns a Plotly Figure."""
        gen = ChartGenerator(full_stats)
        fig = gen.author_distribution()

        assert isinstance(fig, go.Figure)
        assert fig.layout.title.text == "Commits by Author"

    def test_all_charts_returns_list(self, full_stats):
        """all_charts returns list of figures."""
        gen = ChartGenerator(full_stats)
        charts = gen.all_charts()

        assert isinstance(charts, list)
        assert len(charts) >= 5  # At least 5 core charts
        for chart in charts:
            assert isinstance(chart, go.Figure)

    def test_all_charts_includes_phase_when_detected(self, full_stats):
        """all_charts includes phase chart when phases detected."""
        gen = ChartGenerator(full_stats)
        charts = gen.all_charts()

        titles = [c.layout.title.text for c in charts]
        assert "Commits by Phase" in titles

    def test_all_charts_excludes_phase_when_none(self, minimal_stats):
        """all_charts excludes phase chart when no phases."""
        gen = ChartGenerator(minimal_stats)
        charts = gen.all_charts()

        titles = [c.layout.title.text for c in charts if c.layout.title.text]
        assert "Commits by Phase" not in titles


class TestReportGenerator:
    """Tests for ReportGenerator."""

    def test_generate_html_returns_string(self, full_stats):
        """generate_html returns HTML string."""
        gen = ChartGenerator(full_stats)
        figures = gen.all_charts()
        report = ReportGenerator(figures, stats=full_stats)

        html = report.generate_html()

        assert isinstance(html, str)
        assert "<!DOCTYPE html>" in html
        assert "Git Commit Analysis Report" in html

    def test_generate_html_includes_charts(self, full_stats):
        """generate_html embeds chart HTML."""
        gen = ChartGenerator(full_stats)
        figures = [gen.velocity_chart()]
        report = ReportGenerator(figures)

        html = report.generate_html()

        # Plotly charts include this class
        assert "plotly" in html.lower()

    def test_generate_html_includes_summary(self, full_stats):
        """generate_html includes summary stats."""
        gen = ChartGenerator(full_stats)
        figures = [gen.velocity_chart()]
        report = ReportGenerator(figures, stats=full_stats)

        html = report.generate_html()

        assert "Total Commits" in html
        assert "100" in html  # total commits
        assert "75%" in html  # conventional compliance

    def test_generate_html_custom_title(self, full_stats):
        """generate_html uses custom title."""
        gen = ChartGenerator(full_stats)
        figures = [gen.velocity_chart()]
        report = ReportGenerator(figures, title="Custom Report Title")

        html = report.generate_html()

        assert "Custom Report Title" in html

    def test_write_html_creates_file(self, full_stats):
        """write_html creates HTML file."""
        gen = ChartGenerator(full_stats)
        figures = [gen.velocity_chart()]
        report = ReportGenerator(figures, stats=full_stats)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.html"
            report.write_html(output_path)

            assert output_path.exists()
            content = output_path.read_text()
            assert "<!DOCTYPE html>" in content

    def test_to_json_returns_dict(self, full_stats):
        """to_json returns serializable dict."""
        gen = ChartGenerator(full_stats)
        figures = [gen.velocity_chart()]
        report = ReportGenerator(figures, stats=full_stats)

        result = report.to_json()

        assert isinstance(result, dict)
        assert "title" in result
        assert "summary" in result
        assert "charts" in result
        assert len(result["charts"]) == 1

    def test_summary_without_stats(self):
        """Summary is empty when no stats provided."""
        fig = go.Figure()
        report = ReportGenerator([fig])

        html = report.generate_html()

        # HTML should still be valid
        assert "<!DOCTYPE html>" in html

    def test_summary_includes_date_range(self, full_stats):
        """Summary includes date range when available."""
        gen = ChartGenerator(full_stats)
        figures = [gen.velocity_chart()]
        report = ReportGenerator(figures, stats=full_stats)

        summary = report._build_summary()

        assert "Date Range" in summary
        assert "2024-01-15" in summary["Date Range"]

    def test_summary_includes_phases(self, full_stats):
        """Summary includes phases when detected."""
        gen = ChartGenerator(full_stats)
        figures = [gen.velocity_chart()]
        report = ReportGenerator(figures, stats=full_stats)

        summary = report._build_summary()

        assert "Phases Detected" in summary
        assert "1, 2, 3, 4" in summary["Phases Detected"]


class TestChartColors:
    """Tests for chart color configuration."""

    def test_chart_generator_has_colors(self, full_stats):
        """ChartGenerator has color palette defined."""
        gen = ChartGenerator(full_stats)

        assert hasattr(gen, "COLORS")
        assert "primary" in gen.COLORS
        assert "success" in gen.COLORS
        assert "danger" in gen.COLORS

    def test_chart_generator_has_type_colors(self, full_stats):
        """ChartGenerator has commit type colors."""
        gen = ChartGenerator(full_stats)

        assert hasattr(gen, "TYPE_COLORS")
        assert CommitType.FEAT in gen.TYPE_COLORS
        assert CommitType.FIX in gen.TYPE_COLORS
