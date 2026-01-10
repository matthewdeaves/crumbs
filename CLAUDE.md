# Crumbs Quick Reference

## What This Is
A Python CLI tool to analyze git commits and generate visual reports.

## Tech Stack
- Python 3.11+
- Click (CLI framework)
- GitPython (git operations)
- Plotly (charts)
- Jinja2 (HTML templating)
- Rich (terminal output)
- Kaleido (PNG export)

## Key Patterns

### Module Organization
- `models/` - All dataclasses live here, imported elsewhere
- `git/` - GitPython wrapped, never used directly outside this module
- `analysis/` - Takes parsed commits, returns statistics
- `visualization/` - Takes statistics, returns Plotly figures
- `cli.py` - Ties everything together

### Data Flow
```
GitRepository.iter_commits() -> List[Commit]
    -> StatsCalculator(commits) -> RepositoryStats
    -> ChartGenerator(stats) -> List[Figure]
    -> ReportGenerator(figures) -> HTML
```

### Conventions
- Charts return Plotly `Figure` objects, not HTML strings
- All timestamps are UTC
- Commit types follow conventional commits spec

## Commands
```bash
# Development
pip install -e .
pytest tests/ -v

# Usage
crumbs analyze /path/to/repo -o report.html
crumbs stats /path/to/repo
crumbs quality /path/to/repo
```

## Test Repo
```bash
git clone git@github.com:matthewdeaves/cookie.git /tmp/cookie
```
Expected: ~126 commits, ~98% Claude co-authored, ~75% conventional compliance

## Session Workflow
1. Complete session tasks
2. Run verification command for that step
3. `/clear`
4. Start next session
