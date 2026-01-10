# Crumbs - Git Commit History Analyzer

A Python CLI tool to analyze git commits and generate visual reports for blog posts.

## Target Repository Analysis

The cookie repo (`git@github.com:matthewdeaves/cookie.git`) contains:
- 126 commits over 3 days
- 75% follow conventional commits format
- 98% have Claude co-authorship
- Phase-based development (Phase 1-10)

## Project Structure

```
/home/matt/crumbs/
├── pyproject.toml
├── crumbs/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py                    # Click CLI interface
│   ├── config.py
│   ├── git/
│   │   ├── __init__.py
│   │   ├── repository.py         # GitPython wrapper
│   │   └── parser.py             # Commit message parser
│   ├── analysis/
│   │   ├── __init__.py
│   │   ├── stats.py              # Statistical calculations
│   │   └── semantic.py           # Message quality analysis
│   ├── visualization/
│   │   ├── __init__.py
│   │   ├── charts.py             # Plotly chart generators
│   │   ├── report.py             # HTML report generator
│   │   └── templates/
│   │       └── report.html
│   └── models/
│       ├── __init__.py
│       └── dataclasses.py        # Commit, RepositoryStats
└── tests/
    ├── conftest.py               # Pytest fixtures
    ├── test_models.py
    ├── test_parser.py
    ├── test_repository.py
    ├── test_stats.py
    ├── test_charts.py
    └── test_cli.py
```

## Session Scope

| Session | Steps | Deliverable | Verification |
|---------|-------|-------------|--------------|
| 1 | 1-2 | Package skeleton with models + tests | `pytest tests/test_models.py` passes |
| 2 | 3 | Git operations working + tests | Parse commits from test repo, `pytest tests/test_parser.py tests/test_repository.py` passes |
| 3 | 4 | Analysis module complete + tests | Generate stats, `pytest tests/test_stats.py` passes |
| 4 | 5 | Visualization/charts + tests | Render charts to HTML, `pytest tests/test_charts.py` passes, browser verification |
| 5 | 6 | CLI integration + tests | Full `crumbs analyze` command works, `pytest tests/test_cli.py` passes |

**Session workflow:** Complete each session, verify the deliverable, run tests, then `/clear` before starting the next.

## How to Run Sessions

### Starting a Session
```
Read PLAN.md and CLAUDE.md. Implement Session {N}.
Run the verification command before completing.
```

### After Each Session
1. Run the verification command for that step
2. Run pytest for the step's test files
3. Fix any failures before proceeding
4. `/clear`
5. Start next session with the prompt above

### QA Fix Session (Sessions 4-5 if browser issues found)
```
Read PLAN.md QA Issue Log. Research how existing visualization
code handles similar cases. Fix {QA-ID}. Verify in browser.
```

---

## Implementation Steps

### Step 1: Project Setup
- Create `pyproject.toml` with dependencies: click, gitpython, plotly, jinja2, rich
- Create package structure with `__init__.py` files
- Set up CLI entry point: `crumbs = "crumbs.cli:cli"`
- Create `tests/conftest.py` with shared fixtures (sample commits, mock repo)

**Verification:**
```bash
pip install -e .
python -c "import crumbs; print('OK')"
```

### Step 2: Data Models (`crumbs/models/dataclasses.py`)
- `CommitType` enum (feat, fix, docs, test, chore, etc.)
- `CommitStats` dataclass (lines_added, lines_deleted, files_changed)
- `Commit` dataclass (sha, message, author, timestamp, stats, co_authors, phase)
- `RepositoryStats` dataclass (aggregated metrics)

**Verification:**
```bash
python -c "from crumbs.models import Commit, CommitType, CommitStats; print('Models OK')"
```

**Tests (`tests/test_models.py`):**
- Test dataclass instantiation with valid data
- Test CommitType enum values
- Test CommitStats calculations (total changes)
- Test Commit with and without optional fields

```bash
pytest tests/test_models.py -v
```

### Step 3: Git Operations (`crumbs/git/`)
- `repository.py`: GitRepository class wrapping GitPython
  - `iter_commits()` with date/author filters
  - `get_commit_stats()` for diff stats
- `parser.py`: CommitMessageParser class
  - Parse conventional commit format: `type(scope): subject`
  - Extract co-authors from `Co-Authored-By:` trailer
  - Detect phase references

**Verification (Minimal Working Core):**
```bash
# Clone test repo first
git clone git@github.com:matthewdeaves/cookie.git /tmp/cookie

# Test git operations
python -c "
from crumbs.git import GitRepository
repo = GitRepository('/tmp/cookie')
commits = list(repo.iter_commits())
print(f'Parsed {len(commits)} commits - Git OK')
"
```
This is the "Land" milestone - basic functionality works before building analysis/visualization.

**Tests (`tests/test_parser.py`, `tests/test_repository.py`):**
- `test_parser.py`: Parse conventional commit formats, extract co-authors, detect phases, handle malformed messages
- `test_repository.py`: GitRepository with fixture repo, test iter_commits filters, test get_commit_stats

```bash
pytest tests/test_parser.py tests/test_repository.py -v
```

### Step 4: Analysis (`crumbs/analysis/`)
- `stats.py`: StatsCalculator class
  - Commits by day/hour
  - Time between commits
  - Commit size buckets (small/medium/large/xlarge)
  - Work session detection
- `semantic.py`: SemanticAnalyzer class
  - Conventional commit compliance check
  - Basic sentiment scoring
  - Specificity scoring (vague vs precise messages)

**Verification:**
```bash
python -c "
from crumbs.git import GitRepository
from crumbs.analysis import StatsCalculator
repo = GitRepository('/tmp/cookie')
commits = list(repo.iter_commits())
stats = StatsCalculator(commits)
print(f'Total commits: {stats.total_commits}')
print(f'Conventional compliance: {stats.conventional_compliance:.0%}')
print('Analysis OK')
"
```

**Tests (`tests/test_stats.py`):**
- Test StatsCalculator with known commit data
- Test commit bucketing logic (small/medium/large/xlarge)
- Test conventional compliance calculation
- Test work session detection

```bash
pytest tests/test_stats.py -v
```

### Step 5: Visualization (`crumbs/visualization/`)
- `charts.py`: ChartGenerator class using Plotly
  - `velocity_chart()` - commits over time
  - `commit_size_histogram()` - size distribution
  - `phase_burndown()` - phase completion over time
  - `code_churn_chart()` - additions vs deletions
  - `hourly_heatmap()` - activity by hour
  - `type_distribution()` - pie chart of commit types
- `report.py`: ReportGenerator using Jinja2
  - Embed charts as self-contained HTML
  - Summary stats section
  - Export to PNG option

**Verification:**
```bash
python -c "
from crumbs.git import GitRepository
from crumbs.analysis import StatsCalculator
from crumbs.visualization import ChartGenerator
repo = GitRepository('/tmp/cookie')
commits = list(repo.iter_commits())
stats = StatsCalculator(commits)
charts = ChartGenerator(stats)
fig = charts.velocity_chart()
fig.write_html('/tmp/test_chart.html')
print('Chart written to /tmp/test_chart.html - Visualization OK')
"
# Open /tmp/test_chart.html in browser to verify rendering
```

**Tests (`tests/test_charts.py`):**
- Test each chart method returns a Plotly Figure
- Test chart generation with minimal stats data
- Test ReportGenerator produces valid HTML

```bash
pytest tests/test_charts.py -v
```

**Browser Verification:** Open `/tmp/test_chart.html` and verify charts render correctly. Log any issues to the QA Issue Log below.

### Step 6: CLI (`crumbs/cli.py`)
```bash
crumbs analyze [REPO_PATH] -o report.html    # Generate full report
crumbs stats [REPO_PATH]                      # Quick summary
crumbs quality [REPO_PATH]                    # Message quality check
```

Options:
- `--since`, `--until`: Date filters
- `--author`: Filter by author
- `--output`, `-o`: Output file path
- `--format`: html, png, json
- `--verbose`, `-v`: Verbose output

**Verification:**
```bash
crumbs stats /tmp/cookie
crumbs analyze /tmp/cookie -o /tmp/test-report.html
# Open /tmp/test-report.html in browser - all charts should render
crumbs analyze /tmp/cookie --format json -o /tmp/test-report.json
# Verify JSON output is valid
```

**Tests (`tests/test_cli.py`):**
- Test CLI commands with Click's CliRunner
- Test `analyze` command produces output file
- Test `stats` command output format
- Test `quality` command output
- Test option parsing (--since, --author, --format)

```bash
pytest tests/test_cli.py -v
```

**Browser Verification:** Open `/tmp/test-report.html` and verify all charts render. Log any issues to the QA Issue Log below.

---

## QA Issue Log

Track issues found during browser verification (Sessions 4-5).

| ID | Issue | Session | Status |
|----|-------|---------|--------|
| | | | |

**Status values:** New, Fixed, Verified, Won't Fix

**Workflow:**
1. During browser verification, log issues with a unique ID (e.g., QA-001)
2. Add fix tasks to the current session or schedule for next session
3. After fixing, verify in browser and update status

## Dependencies

```toml
dependencies = [
    "click>=8.0",
    "gitpython>=3.1",
    "plotly>=5.0",
    "jinja2>=3.0",
    "rich>=13.0",
    "kaleido>=0.2",  # For PNG export
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
]
```

## Output Formats

1. **HTML** (default): Self-contained interactive report with Plotly charts
2. **PNG**: Static images of each chart via kaleido
3. **JSON**: Raw data for custom processing

## Verification

1. Install the package:
   ```bash
   cd /home/matt/crumbs
   pip install -e .
   ```

2. Clone the cookie repo and run analysis:
   ```bash
   git clone git@github.com:matthewdeaves/cookie.git /tmp/cookie
   crumbs analyze /tmp/cookie -o cookie-report.html
   ```

3. Run all tests:
   ```bash
   pytest tests/ -v
   ```

4. Verify outputs:
   - Open `cookie-report.html` in browser - check all charts render
   - Run `crumbs stats /tmp/cookie` - verify summary output
   - Run `crumbs analyze /tmp/cookie --format png -o ./charts/` - verify PNG export
   - Log any browser issues to the QA Issue Log

5. Expected metrics for cookie repo:
   - 126 total commits
   - ~98% Claude co-authored
   - ~75% conventional commit compliance
   - Phase 1-10 detected
