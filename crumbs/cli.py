"""CLI interface for crumbs."""

import click


@click.group()
@click.version_option()
def cli():
    """Crumbs - Git commit history analyzer."""
    pass


@cli.command()
@click.argument("repo_path", type=click.Path(exists=True))
@click.option("-o", "--output", type=click.Path(), help="Output file path")
@click.option("--format", "output_format", type=click.Choice(["html", "png", "json"]), default="html")
@click.option("--since", help="Only commits after this date")
@click.option("--until", help="Only commits before this date")
@click.option("--author", help="Filter by author")
@click.option("-v", "--verbose", is_flag=True, help="Verbose output")
def analyze(repo_path, output, output_format, since, until, author, verbose):
    """Generate full report for a repository."""
    click.echo(f"Analyzing {repo_path}...")


@cli.command()
@click.argument("repo_path", type=click.Path(exists=True))
@click.option("-v", "--verbose", is_flag=True, help="Verbose output")
def stats(repo_path, verbose):
    """Quick summary statistics."""
    click.echo(f"Stats for {repo_path}...")


@cli.command()
@click.argument("repo_path", type=click.Path(exists=True))
@click.option("-v", "--verbose", is_flag=True, help="Verbose output")
def quality(repo_path, verbose):
    """Message quality check."""
    click.echo(f"Quality check for {repo_path}...")
