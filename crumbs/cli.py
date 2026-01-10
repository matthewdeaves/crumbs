"""CLI interface for crumbs."""

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from crumbs.git.repository import GitRepository, GitRepositoryError
from crumbs.analysis.stats import StatsCalculator
from crumbs.analysis.llm_sentiment import LLMSentimentAnalyzer
from crumbs.visualization.charts import ChartGenerator
from crumbs.visualization.report import ReportGenerator


console = Console()


def parse_date(date_str: str | None) -> datetime | None:
    """Parse a date string into a datetime object.

    Args:
        date_str: Date string in YYYY-MM-DD format, or None

    Returns:
        datetime object or None
    """
    if not date_str:
        return None

    try:
        # Try ISO format first (YYYY-MM-DD)
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.replace(tzinfo=timezone.utc)
    except ValueError:
        pass

    try:
        # Try with time component
        dt = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S")
        return dt.replace(tzinfo=timezone.utc)
    except ValueError:
        raise click.BadParameter(f"Invalid date format: {date_str}. Use YYYY-MM-DD.")


@click.group()
@click.version_option()
def cli():
    """Crumbs - Git commit history analyzer."""
    pass


@cli.command()
@click.argument("repo_path", type=click.Path(exists=True))
@click.option("-o", "--output", type=click.Path(), help="Output directory/file path")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["html", "png", "json"]),
    default="html",
)
@click.option("--since", help="Only commits after this date (YYYY-MM-DD)")
@click.option("--until", help="Only commits before this date (YYYY-MM-DD)")
@click.option("--author", help="Filter by author")
@click.option("--skip-sentiment", is_flag=True, help="Skip LLM sentiment analysis")
@click.option("-v", "--verbose", is_flag=True, help="Verbose output")
def analyze(repo_path, output, output_format, since, until, author, skip_sentiment, verbose):
    """Generate full report for a repository."""
    try:
        # Parse date filters
        since_dt = parse_date(since)
        until_dt = parse_date(until)

        # Open repository
        if verbose:
            console.print(f"Opening repository: {repo_path}")
        repo = GitRepository(repo_path)

        # Collect commits
        if verbose:
            console.print("Collecting commits...")
        commits = list(repo.iter_commits(since=since_dt, until=until_dt, author=author))

        if not commits:
            console.print("[yellow]No commits found matching criteria.[/yellow]")
            return

        if verbose:
            console.print(f"Found {len(commits)} commits")

        # Calculate statistics
        if verbose:
            console.print("Calculating statistics...")
        calculator = StatsCalculator(commits)
        stats = calculator.calculate()

        # Run LLM sentiment analysis (if not skipped)
        sentiment_results = []
        if not skip_sentiment:
            analyzer = LLMSentimentAnalyzer()
            if analyzer.available:
                console.print("Running LLM sentiment analysis...")
                sentiment_results = asyncio.run(analyzer.analyze_commits(commits))
                console.print(f"[green]Analyzed {len(sentiment_results)} commits[/green]")
            elif verbose:
                console.print("[dim]LLM sentiment disabled (no API key)[/dim]")

        # Generate charts
        if verbose:
            console.print("Generating charts...")
        chart_gen = ChartGenerator(stats)
        figures = chart_gen.all_charts()

        # Add sentiment chart if we have results
        if sentiment_results:
            sentiment_fig = chart_gen.sentiment_chart(sentiment_results)
            figures.append(sentiment_fig)

        # Create report generator
        report = ReportGenerator(
            figures=figures,
            stats=stats,
            title=f"Git Analysis: {repo.name}",
            sentiment_results=sentiment_results,
            repo_path=str(repo_path),
        )

        # Determine output path
        if not output:
            if output_format == "html":
                output = "./report"
            elif output_format == "png":
                output = "charts"
            else:
                output = "report.json"

        # Generate output
        if output_format == "html":
            # Use landing page for HTML output
            index_path = report.write_landing_page(output)
            console.print(f"[green]Report written to {index_path}[/green]")

        elif output_format == "png":
            output_path = Path(output)
            exported = report.export_png(output_path)
            console.print(f"[green]Exported {len(exported)} charts to {output}/[/green]")
            if verbose:
                for path in exported:
                    console.print(f"  - {path.name}")

        elif output_format == "json":
            data = report.to_json()
            Path(output).write_text(json.dumps(data, indent=2, default=str))
            console.print(f"[green]JSON written to {output}[/green]")

    except GitRepositoryError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        if verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


@cli.command()
@click.argument("repo_path", type=click.Path(exists=True))
@click.option("--since", help="Only commits after this date (YYYY-MM-DD)")
@click.option("--until", help="Only commits before this date (YYYY-MM-DD)")
@click.option("--author", help="Filter by author")
@click.option("-v", "--verbose", is_flag=True, help="Verbose output")
def stats(repo_path, since, until, author, verbose):
    """Quick summary statistics."""
    try:
        # Parse date filters
        since_dt = parse_date(since)
        until_dt = parse_date(until)

        # Open repository
        repo = GitRepository(repo_path)

        # Collect commits
        commits = list(repo.iter_commits(since=since_dt, until=until_dt, author=author))

        if not commits:
            console.print("[yellow]No commits found matching criteria.[/yellow]")
            return

        # Calculate statistics
        calculator = StatsCalculator(commits)
        stats_data = calculator.calculate()

        # Display summary table
        table = Table(title=f"Repository Stats: {repo.name}")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Total Commits", f"{stats_data.total_commits:,}")
        table.add_row("Lines Added", f"{stats_data.total_lines_added:,}")
        table.add_row("Lines Deleted", f"{stats_data.total_lines_deleted:,}")
        table.add_row("Files Changed", f"{stats_data.total_files_changed:,}")
        table.add_row(
            "Conventional Compliance", f"{stats_data.conventional_compliance:.1%}"
        )
        table.add_row("Co-Authored", f"{stats_data.co_authored_percentage:.1%}")
        table.add_row("Work Sessions", str(stats_data.work_sessions))

        if stats_data.first_commit_date and stats_data.last_commit_date:
            table.add_row(
                "Date Range",
                f"{stats_data.first_commit_date.strftime('%Y-%m-%d')} to "
                f"{stats_data.last_commit_date.strftime('%Y-%m-%d')}",
            )

        console.print(table)

        # Verbose: show commit type breakdown
        if verbose and stats_data.commits_by_type:
            type_table = Table(title="Commits by Type")
            type_table.add_column("Type", style="cyan")
            type_table.add_column("Count", style="green")
            type_table.add_column("Percentage", style="yellow")

            for commit_type, count in sorted(
                stats_data.commits_by_type.items(),
                key=lambda x: x[1],
                reverse=True,
            ):
                pct = count / stats_data.total_commits * 100
                type_table.add_row(commit_type.value, str(count), f"{pct:.1f}%")

            console.print(type_table)

        # Verbose: show author breakdown
        if verbose and stats_data.commits_by_author:
            author_table = Table(title="Commits by Author")
            author_table.add_column("Author", style="cyan")
            author_table.add_column("Count", style="green")
            author_table.add_column("Percentage", style="yellow")

            for author_name, count in sorted(
                stats_data.commits_by_author.items(),
                key=lambda x: x[1],
                reverse=True,
            ):
                pct = count / stats_data.total_commits * 100
                author_table.add_row(author_name, str(count), f"{pct:.1f}%")

            console.print(author_table)

    except GitRepositoryError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.argument("repo_path", type=click.Path(exists=True))
@click.option("--since", help="Only commits after this date (YYYY-MM-DD)")
@click.option("--until", help="Only commits before this date (YYYY-MM-DD)")
@click.option("--author", help="Filter by author")
@click.option("-v", "--verbose", is_flag=True, help="Verbose output")
def quality(repo_path, since, until, author, verbose):
    """Message quality check."""
    try:
        # Parse date filters
        since_dt = parse_date(since)
        until_dt = parse_date(until)

        # Open repository
        repo = GitRepository(repo_path)

        # Collect commits
        commits = list(repo.iter_commits(since=since_dt, until=until_dt, author=author))

        if not commits:
            console.print("[yellow]No commits found matching criteria.[/yellow]")
            return

        # Calculate statistics
        calculator = StatsCalculator(commits)
        stats_data = calculator.calculate()

        # Quality metrics
        conventional_pct = stats_data.conventional_compliance * 100
        co_authored_pct = stats_data.co_authored_percentage * 100

        # Determine quality grade
        if conventional_pct >= 90:
            grade = "A"
            grade_color = "green"
        elif conventional_pct >= 75:
            grade = "B"
            grade_color = "green"
        elif conventional_pct >= 60:
            grade = "C"
            grade_color = "yellow"
        elif conventional_pct >= 40:
            grade = "D"
            grade_color = "yellow"
        else:
            grade = "F"
            grade_color = "red"

        # Display quality report
        console.print(f"\n[bold]Commit Quality Report: {repo.name}[/bold]\n")

        table = Table()
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        table.add_column("Status")

        # Conventional commits
        conv_status = (
            "[green]Good[/green]"
            if conventional_pct >= 75
            else "[yellow]Needs work[/yellow]"
        )
        table.add_row(
            "Conventional Commits",
            f"{stats_data.conventional_count}/{stats_data.total_commits} ({conventional_pct:.1f}%)",
            conv_status,
        )

        # Co-authored commits
        co_status = (
            "[green]Good[/green]"
            if co_authored_pct >= 50
            else "[yellow]Low collaboration[/yellow]"
        )
        table.add_row(
            "Co-Authored Commits",
            f"{stats_data.co_authored_count}/{stats_data.total_commits} ({co_authored_pct:.1f}%)",
            co_status,
        )

        # Commit types used
        types_used = len(stats_data.commits_by_type)
        types_status = (
            "[green]Good variety[/green]" if types_used >= 3 else "[yellow]Limited[/yellow]"
        )
        table.add_row("Commit Types Used", str(types_used), types_status)

        console.print(table)

        # Overall grade
        console.print(
            f"\n[bold]Overall Grade: [{grade_color}]{grade}[/{grade_color}][/bold]"
        )

        # Verbose: show non-conventional commits
        if verbose:
            non_conventional = [c for c in commits if not c.is_conventional]
            if non_conventional:
                console.print(
                    f"\n[yellow]Non-conventional commits ({len(non_conventional)}):[/yellow]"
                )
                for commit in non_conventional[:10]:  # Limit to 10
                    short_sha = commit.sha[:8]
                    first_line = commit.message.split("\n")[0][:60]
                    console.print(f"  {short_sha}: {first_line}")
                if len(non_conventional) > 10:
                    console.print(f"  ... and {len(non_conventional) - 10} more")

    except GitRepositoryError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)
