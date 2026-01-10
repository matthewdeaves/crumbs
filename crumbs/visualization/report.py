"""HTML report generator using Jinja2."""

import json
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
import plotly.graph_objects as go

from crumbs.models import RepositoryStats, SentimentResult


class ReportGenerator:
    """Generate HTML reports from charts and statistics.

    Uses Jinja2 templates to create self-contained HTML reports
    with embedded Plotly charts.
    """

    def __init__(
        self,
        figures: list[go.Figure],
        stats: RepositoryStats | None = None,
        title: str = "Git Commit Analysis Report",
        sentiment_results: list[SentimentResult] | None = None,
        repo_path: str | None = None,
    ):
        """Initialize the report generator.

        Args:
            figures: List of Plotly Figure objects to include
            stats: Optional RepositoryStats for summary section
            title: Report title
            sentiment_results: Optional list of sentiment analysis results
            repo_path: Optional repository path for display
        """
        self.figures = figures
        self.stats = stats
        self.title = title
        self.sentiment_results = sentiment_results or []
        self.repo_path = repo_path

        # Set up Jinja2 environment
        template_dir = Path(__file__).parent / "templates"
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=True,
        )

    def generate_html(self, include_plotlyjs: bool = True) -> str:
        """Generate HTML report with embedded charts.

        Args:
            include_plotlyjs: Whether to include Plotly.js library
                             (set False if loading from CDN in template)

        Returns:
            Complete HTML document as string
        """
        template = self.env.get_template("report.html")

        # Convert figures to HTML divs
        chart_htmls = []
        for fig in self.figures:
            # Generate HTML div without full page wrapper
            chart_html = fig.to_html(
                full_html=False,
                include_plotlyjs=False,  # Template loads from CDN
            )
            chart_htmls.append(chart_html)

        # Build summary dict
        summary = self._build_summary()

        return template.render(
            title=self.title,
            summary=summary,
            charts=chart_htmls,
        )

    def write_html(self, output_path: str | Path) -> None:
        """Write HTML report to file.

        Args:
            output_path: Path to write the HTML file
        """
        html = self.generate_html()
        Path(output_path).write_text(html)

    def export_png(self, output_dir: str | Path) -> list[Path]:
        """Export charts as PNG files.

        Args:
            output_dir: Directory to write PNG files

        Returns:
            List of paths to generated PNG files
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        exported = []
        for i, fig in enumerate(self.figures):
            # Get title from figure layout or use index
            title = fig.layout.title.text if fig.layout.title.text else f"chart_{i}"
            # Sanitize filename
            filename = "".join(c if c.isalnum() or c in "._- " else "_" for c in title)
            filename = filename.strip().replace(" ", "_").lower()

            png_path = output_path / f"{filename}.png"
            fig.write_image(str(png_path), width=1200, height=600, scale=2)
            exported.append(png_path)

        return exported

    def to_json(self) -> dict:
        """Export report data as JSON-serializable dict.

        Returns:
            Dictionary with stats and chart specifications
        """
        result = {
            "title": self.title,
            "summary": self._build_summary(),
            "charts": [],
        }

        for fig in self.figures:
            result["charts"].append(
                {
                    "title": fig.layout.title.text if fig.layout.title.text else None,
                    "spec": fig.to_json(),
                }
            )

        return result

    def _build_summary(self) -> dict[str, str]:
        """Build summary dictionary for template.

        Returns:
            Dictionary of summary key-value pairs
        """
        if not self.stats:
            return {}

        summary = {
            "Total Commits": f"{self.stats.total_commits:,}",
            "Lines Added": f"{self.stats.total_lines_added:,}",
            "Lines Deleted": f"{self.stats.total_lines_deleted:,}",
            "Files Changed": f"{self.stats.total_files_changed:,}",
            "Conventional Compliance": f"{self.stats.conventional_compliance:.0%}",
            "Co-Authored": f"{self.stats.co_authored_percentage:.0%}",
        }

        if self.stats.first_commit_date and self.stats.last_commit_date:
            summary["Date Range"] = (
                f"{self.stats.first_commit_date.strftime('%Y-%m-%d')} to "
                f"{self.stats.last_commit_date.strftime('%Y-%m-%d')}"
            )

        if self.stats.work_sessions:
            summary["Work Sessions"] = str(self.stats.work_sessions)

        if self.stats.phases_detected:
            phases = ", ".join(str(p) for p in sorted(self.stats.phases_detected))
            summary["Phases Detected"] = phases

        return summary

    def write_landing_page(self, output_dir: str | Path) -> Path:
        """Generate landing page with chart gallery and PNG exports.

        Creates a complete report directory with:
        - index.html: Landing page with chart gallery
        - Individual HTML files for each chart
        - PNG exports of each chart
        - JSON data export

        Args:
            output_dir: Directory to write all report files

        Returns:
            Path to the generated index.html
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Export each chart as HTML and PNG
        chart_data = []
        for i, fig in enumerate(self.figures):
            # Get chart title or use index
            title = fig.layout.title.text if fig.layout.title.text else f"Chart {i + 1}"
            # Sanitize filename
            filename = self._sanitize_filename(title)

            # Write HTML
            html_path = output_path / f"{filename}.html"
            fig.write_html(str(html_path), include_plotlyjs="cdn")

            # Write PNG
            png_path = output_path / f"{filename}.png"
            try:
                fig.write_image(str(png_path), width=1200, height=600, scale=2)
            except Exception:
                # PNG export may fail if kaleido not available
                png_path = None

            # Generate inline HTML for gallery
            inline_html = fig.to_html(full_html=False, include_plotlyjs=False)

            chart_data.append({
                "title": title,
                "html": inline_html,
                "html_file": f"{filename}.html",
                "png_file": f"{filename}.png" if png_path else None,
            })

        # Export JSON data
        json_path = output_path / "data.json"
        json_data = self.to_json()
        json_path.write_text(json.dumps(json_data, indent=2, default=str))

        # Build template context
        template_context = self._build_landing_context(chart_data)

        # Render landing page
        template = self.env.get_template("landing.html")
        html = template.render(**template_context)

        index_path = output_path / "index.html"
        index_path.write_text(html)

        return index_path

    def _build_landing_context(self, chart_data: list[dict]) -> dict:
        """Build context dictionary for landing page template.

        Args:
            chart_data: List of chart info dicts with html, title, files

        Returns:
            Template context dictionary
        """
        # Build summary for stats cards
        summary = {}
        if self.stats:
            summary = {
                "total_commits": f"{self.stats.total_commits:,}",
                "co_authored_pct": f"{self.stats.co_authored_percentage:.0%}",
                "conventional_pct": f"{self.stats.conventional_compliance:.0%}",
                "lines_added": f"+{self.stats.total_lines_added:,}",
                "lines_deleted": f"-{self.stats.total_lines_deleted:,}",
                "work_sessions": self.stats.work_sessions if self.stats.work_sessions else None,
            }

        # Build date range string
        date_range = None
        if self.stats and self.stats.first_commit_date and self.stats.last_commit_date:
            date_range = (
                f"{self.stats.first_commit_date.strftime('%B %d, %Y')} - "
                f"{self.stats.last_commit_date.strftime('%B %d, %Y')}"
            )

        # Build sentiment data
        sentiment = None
        if self.sentiment_results:
            sentiment_counts = {"positive": 0, "neutral": 0, "negative": 0}
            for result in self.sentiment_results:
                s = result.sentiment.lower()
                if s in sentiment_counts:
                    sentiment_counts[s] += 1

            # Generate sentiment chart HTML
            from crumbs.visualization.charts import ChartGenerator

            # Create a minimal stats object for chart generator
            chart_gen = ChartGenerator(self.stats)
            sentiment_fig = chart_gen.sentiment_pie(self.sentiment_results)
            sentiment_html = sentiment_fig.to_html(full_html=False, include_plotlyjs=False)

            sentiment = {
                "positive": sentiment_counts["positive"],
                "neutral": sentiment_counts["neutral"],
                "negative": sentiment_counts["negative"],
                "chart": sentiment_html,
            }

        return {
            "title": self.title,
            "date_range": date_range,
            "repo_path": self.repo_path,
            "summary": summary,
            "sentiment": sentiment,
            "charts": chart_data,
            "json_file": "data.json",
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    def _sanitize_filename(self, title: str) -> str:
        """Sanitize a string for use as a filename.

        Args:
            title: String to sanitize

        Returns:
            Safe filename string
        """
        # Remove or replace unsafe characters
        safe = "".join(c if c.isalnum() or c in "._- " else "_" for c in title)
        # Replace spaces with underscores and lowercase
        return safe.strip().replace(" ", "_").lower()
