# AI Features Implementation Plan

Research and planning document for adding new LLM-powered features to crumbs.

## Current Architecture Summary

The existing LLM sentiment analysis (`analysis/llm_sentiment.py`) provides a solid pattern:

- **Async batching**: Commits grouped into batches (default 5), processed in parallel via `asyncio.gather()`
- **Error resilience**: Failed batches skipped, exceptions collected with `return_exceptions=True`
- **Graceful degradation**: Features disabled when no API key, empty results returned
- **Structured output**: JSON responses parsed into dataclasses (`SentimentResult`)
- **Sync wrapper**: `analyze_commits_sync()` for CLI integration

**Data flow**: `List[Commit]` → `LLMAnalyzer` → `List[ResultDataclass]` → `ChartGenerator` → `ReportGenerator`

---

## Feature 1: Auto-generated Changelog

### Purpose
Generate user-facing release notes from commits, grouped by category (features, fixes, breaking changes, etc.). LLMs understand context better than regex—can identify breaking changes from message content, not just `BREAKING:` prefix.

### Data Model

```python
@dataclass
class ChangelogEntry:
    sha: str
    category: str          # "added", "changed", "fixed", "removed", "deprecated", "security", "breaking"
    summary: str           # User-facing description (rewritten from commit message)
    scope: Optional[str]   # Area affected (auth, api, ui, etc.)
    impact: str            # "patch", "minor", "major"
    original_message: str  # For reference

@dataclass
class Changelog:
    entries: list[ChangelogEntry]
    version_suggestion: str  # Based on highest impact: "major", "minor", "patch"
    summary: str            # 1-2 sentence overview of all changes
```

### Implementation Approach

**New file**: `crumbs/analysis/changelog.py`

```python
class ChangelogGenerator:
    """Generate structured changelogs from commits using LLM."""

    PROMPT_TEMPLATE = """
    Analyze these git commits and generate changelog entries.

    For each commit, determine:
    1. category: One of [added, changed, fixed, removed, deprecated, security, breaking]
    2. summary: Rewrite as user-facing description (imperative mood, no SHA references)
    3. scope: Area affected (extract from conventional scope or infer from message)
    4. impact: patch (bug fixes), minor (new features), major (breaking changes)

    Commits:
    {commits}

    Return JSON array:
    [{"sha": "...", "category": "...", "summary": "...", "scope": "...", "impact": "..."}]
    """

    async def generate(self, commits: list[Commit]) -> Changelog:
        # Batch and analyze like sentiment
        # Aggregate into Changelog with version suggestion
```

**Batching strategy**: 10 commits per batch (changelog entries are shorter than sentiment analysis)

**Output formats**:
- Markdown (Keep a Changelog format)
- JSON (for programmatic use)
- HTML section in report

### CLI Integration

```bash
crumbs changelog /path/to/repo                    # Generate for all commits
crumbs changelog /path/to/repo --since v1.0.0    # Since a tag/commit
crumbs changelog /path/to/repo --format md       # Output format (md, json, html)
```

### Visualization

Add to report:
- Changelog section with collapsible categories
- Timeline view showing when breaking changes occurred
- Category distribution pie chart

### Prompt Engineering Considerations

- Emphasize user-facing language: "Add dark mode support" not "feat(ui): implement dark mode toggle component"
- Identify breaking changes from context: "changes API response format" → breaking
- Group related commits: Multiple commits for same feature → single entry
- Handle squash commits: Extract multiple changes from long messages

### Cost Estimate

~10 commits/batch × ~500 tokens/batch = ~50 tokens/commit
161 commits ≈ 8,050 tokens ≈ $0.02 with claude-3-haiku

---

## Feature 2: Commit Quality Scoring

### Purpose
Rate each commit message on clarity, specificity, and actionability. Flag vague messages ("fix bug", "updates", "wip") and provide improvement suggestions.

### Data Model

```python
@dataclass
class QualityScore:
    sha: str
    overall_score: float        # 0.0 to 1.0
    clarity_score: float        # Is the intent clear?
    specificity_score: float    # Does it say WHAT was changed?
    actionability_score: float  # Could someone understand without reading code?
    issues: list[str]           # ["Vague subject", "Missing scope", "No context for why"]
    suggestions: list[str]      # ["Specify which bug was fixed", "Add affected component"]
    improved_message: str       # LLM-suggested rewrite

@dataclass
class QualityReport:
    scores: list[QualityScore]
    average_score: float
    grade: str                  # A, B, C, D, F
    common_issues: dict[str, int]  # Issue → count
    worst_offenders: list[QualityScore]  # Bottom 5
```

### Implementation Approach

**New file**: `crumbs/analysis/quality.py`

```python
class CommitQualityAnalyzer:
    """Analyze commit message quality using LLM."""

    PROMPT_TEMPLATE = """
    Rate these commit messages on quality. For each:

    1. clarity_score (0-1): Is the intent immediately clear?
    2. specificity_score (0-1): Does it specify WHAT changed, not just "fix" or "update"?
    3. actionability_score (0-1): Could someone understand the change without reading code?
    4. issues: List specific problems (e.g., "Vague verb", "Missing context")
    5. suggestions: Actionable improvements
    6. improved_message: Rewrite following conventional commits format

    Scoring guide:
    - 0.9-1.0: Excellent - clear, specific, follows conventions
    - 0.7-0.9: Good - minor improvements possible
    - 0.5-0.7: Adequate - functional but could be clearer
    - 0.3-0.5: Poor - vague or missing context
    - 0.0-0.3: Bad - meaningless (e.g., "fix", "wip", "updates")

    Commits:
    {commits}
    """
```

**Batching strategy**: 5 commits per batch (detailed analysis requires more tokens)

### CLI Integration

```bash
crumbs quality /path/to/repo                     # Existing command, enhanced
crumbs quality /path/to/repo --detailed          # Show all scores and suggestions
crumbs quality /path/to/repo --worst 10          # Show 10 worst commits
crumbs quality /path/to/repo --author "John"     # Filter by author
```

### Visualization

Add to report:
- Quality score histogram
- Quality trend over time (are messages improving?)
- Author quality comparison (if multiple authors)
- Common issues word cloud or bar chart
- "Hall of Shame" section with worst messages and suggested rewrites

### Existing Code Integration

The existing `SemanticAnalyzer` in `analysis/semantic.py` does word-based quality scoring:
- `check_conventional_compliance()` - regex-based
- `calculate_specificity()` - word lists (vague words, code identifiers)
- `analyze_sentiment()` - word lists (positive/negative words)

**Strategy**: Keep `SemanticAnalyzer` as fast fallback, add `CommitQualityAnalyzer` for LLM-powered deep analysis. The LLM can:
- Understand context that word lists miss
- Generate actionable suggestions
- Rewrite messages properly

### Prompt Engineering Considerations

- Distinguish between "short but clear" vs "short and vague"
- Recognize domain-specific terms as valid specificity
- Weight conventional commit format but don't require it
- Consider the diff size: "Fix typo" is fine for 1-line change

### Cost Estimate

~5 commits/batch × ~800 tokens/batch = ~160 tokens/commit
161 commits ≈ 25,760 tokens ≈ $0.06 with claude-3-haiku

---

## Feature 3: Risk/Complexity Detection

### Purpose
Flag commits that touch sensitive areas or have characteristics suggesting they need extra review. Identify potential risk before problems occur.

### Data Model

```python
@dataclass
class RiskAssessment:
    sha: str
    risk_level: str             # "low", "medium", "high", "critical"
    risk_score: float           # 0.0 to 1.0
    risk_factors: list[str]     # ["Touches authentication", "Large refactor", "No tests"]
    areas_affected: list[str]   # ["auth", "payments", "database"]
    review_suggestions: list[str]  # ["Verify password hashing unchanged", "Check migration rollback"]
    complexity_score: float     # 0.0 to 1.0 based on change scope

@dataclass
class RiskReport:
    assessments: list[RiskAssessment]
    high_risk_commits: list[RiskAssessment]
    risk_by_area: dict[str, int]  # Area → count of risky commits
    risk_trend: list[tuple[str, float]]  # Date → average risk
```

### Implementation Approach

**New file**: `crumbs/analysis/risk.py`

```python
class RiskAnalyzer:
    """Detect risky or complex commits using LLM."""

    # Risk patterns to look for
    SENSITIVE_AREAS = [
        "authentication", "authorization", "passwords", "tokens", "secrets",
        "payments", "billing", "subscriptions", "pricing",
        "database", "migrations", "schemas",
        "security", "encryption", "certificates",
        "permissions", "roles", "access control"
    ]

    PROMPT_TEMPLATE = """
    Analyze these commits for risk and complexity.

    Risk factors to consider:
    - Touches security-sensitive code (auth, crypto, permissions)
    - Modifies payment/billing logic
    - Database migrations or schema changes
    - Large refactors (high lines changed)
    - Removes tests or error handling
    - Changes to configuration or environment handling
    - API changes that could break clients

    For each commit, provide:
    1. risk_level: low, medium, high, or critical
    2. risk_score: 0.0-1.0
    3. risk_factors: List of specific concerns
    4. areas_affected: Which system areas this touches
    5. review_suggestions: What a reviewer should verify
    6. complexity_score: 0.0-1.0 based on change scope

    Consider the commit message AND the file paths/stats provided.

    Commits:
    {commits}
    """

    def _format_commit(self, commit: Commit) -> str:
        # Include file paths from stats for context
        return f"""
        [{commit.sha[:8]}] {commit.subject}
        Files: {commit.stats.files_changed}, +{commit.stats.lines_added}/-{commit.stats.lines_deleted}
        """
```

**Hybrid approach**: Combine LLM analysis with heuristics:
1. **Pre-filter**: Flag commits touching files matching patterns (`**/auth/**`, `**/payment/**`, `**/*migration*`)
2. **LLM analysis**: Deep analysis of flagged commits + sampling of others
3. **Post-process**: Boost risk scores for known-risky file patterns

### CLI Integration

```bash
crumbs risk /path/to/repo                        # Full risk analysis
crumbs risk /path/to/repo --high-only            # Only show high/critical
crumbs risk /path/to/repo --since HEAD~20        # Recent commits only
```

### Visualization

Add to report:
- Risk level distribution pie chart
- Risk timeline (when did risky commits land?)
- Risk heatmap by area (auth, payments, etc.)
- "Needs Review" highlight section with high-risk commits

### File Path Analysis

To improve accuracy, analyze file paths in the diff:

```python
RISKY_PATH_PATTERNS = {
    r"auth|login|session|token|password|credential": "authentication",
    r"payment|billing|subscription|stripe|paypal": "payments",
    r"migration|schema|database": "database",
    r"secret|key|cert|ssl|tls|crypto": "security",
    r"permission|role|access|policy": "authorization",
    r"config|env|setting": "configuration",
}
```

### Prompt Engineering Considerations

- Avoid false positives: "fix auth typo in docs" is not high risk
- Consider context: Large changes to tests are lower risk than small changes to crypto
- Weight removal higher than addition for tests/error handling
- Recognize security fixes as high-priority but positive

### Cost Estimate

~5 commits/batch × ~600 tokens/batch = ~120 tokens/commit
161 commits ≈ 19,320 tokens ≈ $0.05 with claude-3-haiku

---

## Feature 4: Semantic Commit Clustering

### Purpose
Group commits into logical features/epics even if they weren't explicitly tagged. Answer: "What major changes happened in this period?"

### Data Model

```python
@dataclass
class CommitCluster:
    id: str                     # Generated cluster ID
    name: str                   # LLM-generated name: "User Authentication Rework"
    description: str            # 1-2 sentence summary
    commits: list[str]          # List of SHAs
    commit_count: int
    primary_type: CommitType    # Most common type in cluster
    areas: list[str]            # Affected areas
    date_range: tuple[datetime, datetime]
    total_lines_changed: int

@dataclass
class ClusteringResult:
    clusters: list[CommitCluster]
    unclustered: list[str]      # SHAs that don't fit any cluster
    overlap_map: dict[str, list[str]]  # SHA → cluster IDs (if commit fits multiple)
```

### Implementation Approach

**New file**: `crumbs/analysis/clustering.py`

```python
class SemanticClusterer:
    """Group commits into logical features/epics using LLM."""

    PROMPT_TEMPLATE = """
    Group these commits into logical clusters (features, bug fix campaigns, refactors).

    Look for:
    - Related functionality (e.g., all commits about user auth)
    - Sequential work on same feature
    - Related bug fixes
    - Refactoring campaigns

    For each cluster:
    1. name: Descriptive name (e.g., "Dark Mode Implementation")
    2. description: 1-2 sentence summary
    3. commits: List of SHA prefixes belonging to this cluster
    4. areas: System areas affected

    Commits can belong to multiple clusters if they span concerns.
    Mark truly standalone commits as unclustered.

    Commits (chronological order):
    {commits}
    """
```

**Two-phase approach**:

1. **Initial clustering**: Send all commits (summarized) for high-level grouping
2. **Refinement**: For large clusters, re-analyze to find sub-clusters

**Batching strategy**: Different from other features—need full context for clustering:
- First pass: All commits with minimal info (SHA + subject only)
- If > 200 commits: Chunk into time windows, cluster each, then merge similar clusters

### CLI Integration

```bash
crumbs clusters /path/to/repo                    # Show all clusters
crumbs clusters /path/to/repo --min-size 3       # Only clusters with 3+ commits
crumbs clusters /path/to/repo --since 2024-01-01 # Cluster recent work
crumbs clusters /path/to/repo --format tree      # Hierarchical view
```

### Visualization

Add to report:
- Cluster timeline (Gantt-style chart showing cluster lifespans)
- Cluster size distribution
- Cluster network graph (show relationships between clusters)
- "Major Changes" summary section

### Algorithm Considerations

**Challenges**:
- Commits may span multiple concerns
- Chronological gaps in feature work (work on feature, pause, resume)
- Single-commit features vs multi-commit epics

**Solutions**:
- Allow multi-cluster membership with overlap_map
- Use time gaps as soft boundaries, not hard cuts
- Minimum cluster size threshold (default: 2 commits)
- "Unclustered" category for truly standalone work

### Prompt Engineering Considerations

- Emphasize semantic similarity over temporal proximity
- Handle conventional commit types: `feat(auth)` commits likely cluster together
- Recognize refactoring campaigns that touch many areas
- Don't over-cluster: Sometimes commits are truly independent

### Cost Estimate

Full context approach: ~200 tokens/commit for summarization
161 commits ≈ 32,200 tokens ≈ $0.08 with claude-3-haiku

---

## Implementation Order

Recommended sequence based on complexity and dependencies:

### Phase 1: Commit Quality Scoring
- **Why first**: Builds on existing `SemanticAnalyzer` patterns
- **Complexity**: Low-medium (similar to sentiment analysis)
- **Value**: Immediate actionable feedback
- **Dependencies**: None

### Phase 2: Risk/Complexity Detection
- **Why second**: Introduces file path analysis pattern
- **Complexity**: Medium (hybrid LLM + heuristics)
- **Value**: High for teams with security concerns
- **Dependencies**: None

### Phase 3: Auto-generated Changelog
- **Why third**: Benefits from quality scoring (better input = better output)
- **Complexity**: Medium (output formatting, version suggestions)
- **Value**: High for release management
- **Dependencies**: None (but quality scoring improves results)

### Phase 4: Semantic Commit Clustering
- **Why last**: Most complex, needs full-context approach
- **Complexity**: High (global analysis, merging, refinement)
- **Value**: High for understanding project evolution
- **Dependencies**: None (but benefits from all other analyses)

---

## Shared Infrastructure

### Base Analyzer Class

```python
class BaseLLMAnalyzer(ABC):
    """Base class for all LLM-powered analyzers."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        batch_size: int = 5
    ):
        self.api_key = api_key or OPENROUTER_API_KEY
        self.model = model or OPENROUTER_MODEL
        self.batch_size = batch_size

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    @abstractmethod
    def _get_prompt(self, commits: list[Commit]) -> str:
        """Return the prompt for this analyzer."""
        pass

    @abstractmethod
    def _parse_response(self, response: str, commits: list[Commit]) -> list:
        """Parse LLM response into result objects."""
        pass

    async def analyze(self, commits: list[Commit]) -> list:
        """Analyze commits using LLM."""
        if not self.available:
            return []

        batches = self._create_batches(commits)
        async with OpenRouter(api_key=self.api_key) as client:
            tasks = [self._analyze_batch(client, batch) for batch in batches]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        return self._collect_results(results)
```

### Configuration Extensions

```bash
# .env additions
QUALITY_BATCH_SIZE=5
RISK_BATCH_SIZE=5
CHANGELOG_BATCH_SIZE=10
CLUSTERING_BATCH_SIZE=50  # Larger for context
```

### Report Integration

```python
# visualization/report.py additions
class ReportGenerator:
    def write_landing_page(
        self,
        stats: RepositoryStats,
        sentiment: list[SentimentResult],
        quality: list[QualityScore],       # New
        risk: list[RiskAssessment],        # New
        changelog: Changelog,               # New
        clusters: ClusteringResult          # New
    ):
        # Generate sections for each
```

---

## Cost Summary

| Feature | Tokens/Commit | 161 Commits | Cost (Haiku) |
|---------|---------------|-------------|--------------|
| Sentiment (existing) | ~50 | 8,050 | $0.02 |
| Quality Scoring | ~160 | 25,760 | $0.06 |
| Risk Detection | ~120 | 19,320 | $0.05 |
| Changelog | ~50 | 8,050 | $0.02 |
| Clustering | ~200 | 32,200 | $0.08 |
| **Total** | ~580 | 93,380 | **$0.23** |

All features enabled for 161 commits: ~$0.25 with claude-3-haiku

---

## Testing Strategy

### Unit Tests
- Mock OpenRouter responses for each analyzer
- Test JSON parsing with valid/invalid/edge cases
- Test batching logic
- Test dataclass validation

### Integration Tests
- Run against real repo (cookie) with API key
- Verify output structure
- Check graceful degradation without API key

### Prompt Testing
- Create test suite of commit messages with expected outputs
- Measure consistency across runs
- A/B test prompt variations

---

## Open Questions

1. **Caching**: Should we cache LLM results by commit SHA to avoid re-analysis?
2. **Incremental analysis**: For large repos, only analyze new commits since last run?
3. **Model selection**: Allow per-feature model override? (Haiku for speed, Sonnet for accuracy)
4. **Batch size tuning**: Optimal batch sizes may differ per feature
5. **Concurrency limits**: Should we rate-limit API calls to avoid hitting quotas?
