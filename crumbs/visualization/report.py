"""HTML report generator using Jinja2."""


class ReportGenerator:
    """Generate HTML reports from charts."""

    def __init__(self, figures):
        self.figures = figures

    def generate_html(self):
        """Generate HTML report with embedded charts."""
        raise NotImplementedError("Will be implemented in Session 4")

    def export_png(self, output_dir):
        """Export charts as PNG files."""
        raise NotImplementedError("Will be implemented in Session 4")
