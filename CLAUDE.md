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
- OpenRouter (LLM sentiment analysis - optional)
- python-dotenv (.env configuration)

## Key Patterns

### Module Organization
- `models/` - All dataclasses live here, imported elsewhere
- `git/` - GitPython wrapped, never used directly outside this module
- `analysis/` - Takes parsed commits, returns statistics
  - `semantic.py` - Word-based analysis (fallback, no API needed)
  - `llm_sentiment.py` - Async OpenRouter analysis (optional)
- `visualization/` - Takes statistics, returns Plotly figures
- `cli.py` - Ties everything together
- `config.py` - Loads .env, provides settings

### Data Flow
```
GitRepository.iter_commits() -> List[Commit]
    -> StatsCalculator(commits) -> RepositoryStats
    -> LLMSentimentAnalyzer(commits) -> List[SentimentResult]  # async, optional
    -> ChartGenerator(stats, sentiment) -> Dict[str, Figure]
    -> ReportGenerator(figures) -> landing page + charts
```

### Conventions
- Charts return Plotly `Figure` objects, not HTML strings
- All timestamps are UTC
- Commit types follow conventional commits spec
- LLM calls are async with `asyncio.gather()` for parallel batches
- Graceful degradation: LLM features disabled if no API key

### Environment Variables
```bash
OPENROUTER_API_KEY=sk-or-...     # Required for LLM sentiment
OPENROUTER_MODEL=anthropic/claude-3-haiku  # Default model
SENTIMENT_BATCH_SIZE=5            # Commits per API call
```

## Commands
```bash
# Development
pip install -e .
pytest tests/ -v

# Usage
crumbs analyze /path/to/repo -o ./report    # Generates report/index.html + charts
crumbs analyze /path/to/repo --skip-sentiment  # Skip LLM analysis
crumbs stats /path/to/repo                  # Quick terminal stats
crumbs quality /path/to/repo                # Commit message quality check
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
