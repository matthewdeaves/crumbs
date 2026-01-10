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
├── .env.example                  # Environment template
├── .env                          # Local config (gitignored)
├── crumbs/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py                    # Click CLI interface
│   ├── config.py                 # Config + env loading
│   ├── git/
│   │   ├── __init__.py
│   │   ├── repository.py         # GitPython wrapper
│   │   └── parser.py             # Commit message parser
│   ├── analysis/
│   │   ├── __init__.py
│   │   ├── stats.py              # Statistical calculations
│   │   ├── semantic.py           # Word-based quality analysis (fallback)
│   │   └── llm_sentiment.py      # Async OpenRouter sentiment analysis
│   ├── visualization/
│   │   ├── __init__.py
│   │   ├── charts.py             # Plotly chart generators
│   │   ├── report.py             # HTML report generator
│   │   └── templates/
│   │       ├── report.html       # Single report template
│   │       └── landing.html      # Landing page with chart gallery
│   └── models/
│       ├── __init__.py
│       └── dataclasses.py        # Commit, RepositoryStats, SentimentResult
└── tests/
    ├── conftest.py               # Pytest fixtures
    ├── test_models.py
    ├── test_parser.py
    ├── test_repository.py
    ├── test_stats.py
    ├── test_charts.py
    ├── test_llm_sentiment.py     # Mock API tests
    └── test_cli.py
```

## Environment Configuration

Create `.env` file (copy from `.env.example`):

```bash
# OpenRouter API (optional - enables LLM sentiment analysis)
OPENROUTER_API_KEY=sk-or-v1-your-key-here

# LLM Settings
OPENROUTER_MODEL=anthropic/claude-3-haiku  # Default: fast and cheap
SENTIMENT_BATCH_SIZE=5                      # Commits per API call (1-20)

# Optional overrides
# OPENROUTER_MODEL=anthropic/claude-3.5-sonnet  # More nuanced analysis
# SENTIMENT_BATCH_SIZE=10                        # Faster for large repos
```

**Behavior:**
- If `OPENROUTER_API_KEY` is set: Uses LLM for rich sentiment analysis
- If not set: Falls back to word-matching in `semantic.py` (no API needed)

## Session Scope

| Session | Steps | Deliverable | Verification |
|---------|-------|-------------|--------------|
| 1 | 1-2 | Package skeleton with models + tests | `pytest tests/test_models.py` passes |
| 2 | 3 | Git operations working + tests | Parse commits from test repo, `pytest tests/test_parser.py tests/test_repository.py` passes |
| 3 | 4 | Analysis module complete + tests | Generate stats, `pytest tests/test_stats.py` passes |
| 4 | 5 | Visualization/charts + tests | Render charts to HTML, `pytest tests/test_charts.py` passes, browser verification |
| 5 | 6 | CLI integration + tests | Full `crumbs analyze` command works, `pytest tests/test_cli.py` passes |
| 6 | 7 | LLM sentiment analysis + tests | Async batched sentiment works, `pytest tests/test_llm_sentiment.py` passes |
| 7 | 8 | Landing page + sentiment chart | Full report with gallery, sentiment visualization, browser verification |

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

### Step 7: LLM Sentiment Analysis (`crumbs/analysis/llm_sentiment.py`)

Async batched sentiment analysis using OpenRouter API with Claude Haiku.

**New dataclass** (`models/dataclasses.py`):
```python
@dataclass
class SentimentResult:
    """LLM sentiment analysis result for a commit."""
    sha: str
    sentiment: str          # "positive", "neutral", "negative"
    confidence: float       # 0.0 to 1.0
    tone: str               # e.g., "enthusiastic", "frustrated", "matter-of-fact"
    summary: str            # Brief interpretation of the commit's intent
```

**Implementation** (`analysis/llm_sentiment.py`):
```python
class LLMSentimentAnalyzer:
    """Async batched sentiment analysis via OpenRouter."""

    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.model = os.getenv("OPENROUTER_MODEL", "anthropic/claude-3-haiku")
        self.batch_size = int(os.getenv("SENTIMENT_BATCH_SIZE", "5"))
        self.available = bool(self.api_key)

    async def analyze_commits(self, commits: list[Commit]) -> list[SentimentResult]:
        """Analyze all commits in batches asynchronously."""
        if not self.available:
            return []  # Caller should fall back to semantic.py

        results = []
        batches = [commits[i:i+self.batch_size]
                   for i in range(0, len(commits), self.batch_size)]

        async with OpenRouter(api_key=self.api_key) as client:
            tasks = [self._analyze_batch(client, batch) for batch in batches]
            batch_results = await asyncio.gather(*tasks)
            for batch in batch_results:
                results.extend(batch)

        return results

    async def _analyze_batch(self, client, commits: list[Commit]) -> list[SentimentResult]:
        """Analyze a single batch of commits."""
        # Build prompt with commit messages
        # Request structured JSON response
        # Parse and return SentimentResult list
```

**Key design decisions:**
- Default batch size: 5 commits (configurable via `SENTIMENT_BATCH_SIZE`)
- Default model: `anthropic/claude-3-haiku` (fast, ~$0.00025/1K tokens)
- All batches run concurrently with `asyncio.gather()`
- Returns empty list if no API key (graceful degradation)

**Config updates** (`config.py`):
```python
from dotenv import load_dotenv

load_dotenv()

# Existing config...

# LLM Settings
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "anthropic/claude-3-haiku")
SENTIMENT_BATCH_SIZE = int(os.getenv("SENTIMENT_BATCH_SIZE", "5"))
LLM_AVAILABLE = bool(OPENROUTER_API_KEY)
```

**Verification:**
```bash
# With API key set in .env
python -c "
import asyncio
from crumbs.git import GitRepository
from crumbs.analysis.llm_sentiment import LLMSentimentAnalyzer

repo = GitRepository('/tmp/cookie')
commits = list(repo.iter_commits())[:10]  # Test with 10 commits
analyzer = LLMSentimentAnalyzer()

if analyzer.available:
    results = asyncio.run(analyzer.analyze_commits(commits))
    print(f'Analyzed {len(results)} commits via LLM')
    for r in results[:3]:
        print(f'  {r.sha[:8]}: {r.sentiment} ({r.tone})')
else:
    print('No API key - LLM sentiment disabled (this is OK)')
"
```

**Tests (`tests/test_llm_sentiment.py`):**
- Test with mocked OpenRouter responses (no real API calls in tests)
- Test batch splitting logic (e.g., 12 commits with batch_size=5 → 3 batches)
- Test graceful handling when API key not set
- Test JSON response parsing
- Test error handling for API failures

```bash
pytest tests/test_llm_sentiment.py -v
```

### Step 8: Landing Page & Sentiment Visualization

Create a polished HTML landing page with chart gallery and sentiment visualization.

**New template** (`visualization/templates/landing.html`):
- Hero section with repository name and date range
- Summary stats cards (total commits, co-authored %, compliance %)
- Chart gallery with thumbnails linking to full charts
- Sentiment breakdown section (if LLM analysis ran)
- All charts embedded as interactive Plotly figures
- Export buttons (download as PNG, JSON)

**New chart** (`visualization/charts.py`):
```python
def sentiment_chart(self) -> Figure:
    """Sentiment distribution across commits."""
    # Pie/donut chart: positive/neutral/negative
    # Timeline: sentiment trend over time
    # Tone breakdown: bar chart of detected tones
```

**Enhanced ReportGenerator** (`visualization/report.py`):
```python
class ReportGenerator:
    def __init__(self, figures, stats, title, sentiment_results=None):
        self.sentiment_results = sentiment_results or []

    def write_landing_page(self, output_dir: Path):
        """Generate landing page with chart gallery and PNG exports."""
        output_dir.mkdir(exist_ok=True)

        # Export each chart as HTML and PNG
        for name, fig in self.figures.items():
            fig.write_html(output_dir / f"{name}.html")
            fig.write_image(output_dir / f"{name}.png")

        # Generate index.html with gallery
        html = self._render_landing_template()
        (output_dir / "index.html").write_text(html)
```

**CLI updates** (`cli.py`):
```python
@cli.command()
@click.argument("repo_path", type=click.Path(exists=True))
@click.option("-o", "--output", type=click.Path(), default="./report")
@click.option("--skip-sentiment", is_flag=True, help="Skip LLM sentiment analysis")
# ... other options
def analyze(repo_path, output, skip_sentiment, ...):
    # ... existing code ...

    # Run LLM sentiment (async) in parallel with chart generation
    sentiment_results = []
    if not skip_sentiment:
        from crumbs.analysis.llm_sentiment import LLMSentimentAnalyzer
        analyzer = LLMSentimentAnalyzer()
        if analyzer.available:
            console.print("Running LLM sentiment analysis...")
            sentiment_results = asyncio.run(analyzer.analyze_commits(commits))
            console.print(f"[green]Analyzed {len(sentiment_results)} commits[/green]")

    # Generate report with sentiment data
    report = ReportGenerator(
        figures=figures,
        stats=stats,
        title=f"Git Analysis: {repo.name}",
        sentiment_results=sentiment_results,
    )

    # Write landing page with all assets
    report.write_landing_page(Path(output))
    console.print(f"[green]Report written to {output}/index.html[/green]")
```

**Verification:**
```bash
# Full analysis with LLM sentiment
crumbs analyze /tmp/cookie -o /tmp/cookie-report

# Check output structure
ls /tmp/cookie-report/
# Expected: index.html, velocity.html, velocity.png, sentiment.html, sentiment.png, ...

# Open landing page
xdg-open /tmp/cookie-report/index.html
```

**Browser Verification Checklist:**
- [ ] Landing page loads with repository summary
- [ ] All chart thumbnails visible and clickable
- [ ] Full charts open in new page/modal
- [ ] Sentiment section shows if LLM was used
- [ ] PNG export links work
- [ ] Responsive on mobile viewport

---

## QA Issue Log

Track issues found during browser verification (Sessions 4-5, 7).

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
    "kaleido>=0.2",           # PNG export
    "python-dotenv>=1.0",     # .env file loading
    "openrouter>=0.1",        # LLM API (sentiment analysis)
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-asyncio>=0.23",   # Async test support
]
```

**Cost estimate (126 commits, batch_size=5):**
- ~26 API calls to Claude Haiku
- ~$0.01-0.02 total (Haiku is very cheap)

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

2. Set up environment (optional, enables LLM sentiment):
   ```bash
   cp .env.example .env
   # Edit .env and add your OpenRouter API key
   ```

3. Clone the cookie repo and run full analysis:
   ```bash
   git clone git@github.com:matthewdeaves/cookie.git /tmp/cookie
   crumbs analyze /tmp/cookie -o /tmp/cookie-report
   ```

4. Run all tests:
   ```bash
   pytest tests/ -v
   ```

5. Verify outputs:
   - Open `/tmp/cookie-report/index.html` in browser - landing page with chart gallery
   - Check sentiment section appears (if API key was set)
   - Click through chart thumbnails - each opens full interactive chart
   - Run `crumbs stats /tmp/cookie` - verify summary output
   - Run `crumbs analyze /tmp/cookie --skip-sentiment -o /tmp/no-llm` - works without API
   - Log any browser issues to the QA Issue Log

6. Expected metrics for cookie repo:
   - 126 total commits
   - ~98% Claude co-authored
   - ~75% conventional commit compliance
   - Phase 1-10 detected
   - Sentiment distribution (with API): mostly positive/neutral (feature-focused commits)
