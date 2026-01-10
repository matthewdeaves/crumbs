"""Tests for LLM sentiment analysis."""

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from crumbs.models import Commit, CommitStats, SentimentResult
from crumbs.analysis.llm_sentiment import LLMSentimentAnalyzer


@pytest.fixture
def mock_commits():
    """Create a list of commits for testing."""
    commits = []
    messages = [
        "feat(auth): add login functionality",
        "fix(api): resolve timeout issue",
        "chore: cleanup old code",
        "docs: update README",
        "refactor: simplify data flow",
    ]
    for i, msg in enumerate(messages):
        commits.append(
            Commit(
                sha=f"abc{i:03d}def",
                message=msg,
                author="Test Author",
                author_email="test@example.com",
                timestamp=datetime(2024, 1, 15, 10 + i, 0, 0, tzinfo=timezone.utc),
                stats=CommitStats(lines_added=10, lines_deleted=5, files_changed=2),
            )
        )
    return commits


@pytest.fixture
def mock_api_response():
    """Create a mock API response."""
    return json.dumps([
        {"sha": "abc000de", "sentiment": "positive", "confidence": 0.9, "tone": "enthusiastic", "summary": "Adding new authentication feature"},
        {"sha": "abc001de", "sentiment": "neutral", "confidence": 0.8, "tone": "matter-of-fact", "summary": "Fixing API timeout bug"},
        {"sha": "abc002de", "sentiment": "neutral", "confidence": 0.7, "tone": "routine", "summary": "Cleaning up codebase"},
        {"sha": "abc003de", "sentiment": "positive", "confidence": 0.85, "tone": "helpful", "summary": "Improving documentation"},
        {"sha": "abc004de", "sentiment": "positive", "confidence": 0.75, "tone": "productive", "summary": "Simplifying code structure"},
    ])


class TestSentimentResult:
    """Tests for SentimentResult dataclass."""

    def test_valid_sentiment(self):
        """Test creating SentimentResult with valid data."""
        result = SentimentResult(
            sha="abc123",
            sentiment="positive",
            confidence=0.9,
            tone="enthusiastic",
            summary="Great feature addition",
        )
        assert result.sentiment == "positive"
        assert result.confidence == 0.9
        assert result.tone == "enthusiastic"

    def test_invalid_sentiment_normalized(self):
        """Test that invalid sentiment is normalized to neutral."""
        result = SentimentResult(
            sha="abc123",
            sentiment="invalid",
            confidence=0.5,
            tone="unknown",
            summary="Test",
        )
        assert result.sentiment == "neutral"

    def test_confidence_clamped(self):
        """Test that confidence is clamped to 0.0-1.0."""
        result_high = SentimentResult(
            sha="abc123",
            sentiment="positive",
            confidence=1.5,
            tone="test",
            summary="Test",
        )
        assert result_high.confidence == 1.0

        result_low = SentimentResult(
            sha="abc123",
            sentiment="negative",
            confidence=-0.5,
            tone="test",
            summary="Test",
        )
        assert result_low.confidence == 0.0


class TestLLMSentimentAnalyzer:
    """Tests for LLMSentimentAnalyzer class."""

    def test_init_defaults(self):
        """Test analyzer initializes with defaults."""
        with patch.dict("os.environ", {}, clear=True):
            analyzer = LLMSentimentAnalyzer(api_key=None)
            assert not analyzer.available
            assert analyzer.batch_size == 5

    def test_init_with_api_key(self):
        """Test analyzer is available when API key provided."""
        analyzer = LLMSentimentAnalyzer(api_key="test-key")
        assert analyzer.available
        assert analyzer.api_key == "test-key"

    def test_init_custom_settings(self):
        """Test analyzer with custom settings."""
        analyzer = LLMSentimentAnalyzer(
            api_key="test-key",
            model="custom/model",
            batch_size=10,
        )
        assert analyzer.model == "custom/model"
        assert analyzer.batch_size == 10

    @pytest.mark.asyncio
    async def test_analyze_commits_no_api_key(self, mock_commits):
        """Test that analyze_commits returns empty list without API key."""
        analyzer = LLMSentimentAnalyzer(api_key=None)
        results = await analyzer.analyze_commits(mock_commits)
        assert results == []

    @pytest.mark.asyncio
    async def test_analyze_commits_empty_list(self):
        """Test that analyze_commits handles empty commit list."""
        analyzer = LLMSentimentAnalyzer(api_key="test-key")
        results = await analyzer.analyze_commits([])
        assert results == []

    def test_batch_splitting(self, mock_commits):
        """Test that commits are split into correct number of batches."""
        analyzer = LLMSentimentAnalyzer(api_key="test-key", batch_size=2)

        # 5 commits with batch_size=2 should give 3 batches
        batches = [
            mock_commits[i : i + analyzer.batch_size]
            for i in range(0, len(mock_commits), analyzer.batch_size)
        ]
        assert len(batches) == 3
        assert len(batches[0]) == 2
        assert len(batches[1]) == 2
        assert len(batches[2]) == 1

    def test_parse_response_valid_json(self, mock_commits, mock_api_response):
        """Test parsing valid JSON response."""
        analyzer = LLMSentimentAnalyzer(api_key="test-key")
        results = analyzer._parse_response(mock_api_response, mock_commits)

        assert len(results) == 5
        assert results[0].sentiment == "positive"
        assert results[0].tone == "enthusiastic"
        assert results[1].sentiment == "neutral"

    def test_parse_response_with_markdown(self, mock_commits):
        """Test parsing response wrapped in markdown code block."""
        analyzer = LLMSentimentAnalyzer(api_key="test-key")
        response = '''```json
[{"sha": "abc000de", "sentiment": "positive", "confidence": 0.9, "tone": "happy", "summary": "Test"}]
```'''
        results = analyzer._parse_response(response, mock_commits[:1])

        assert len(results) == 1
        assert results[0].sentiment == "positive"

    def test_parse_response_invalid_json(self, mock_commits):
        """Test handling of invalid JSON response."""
        analyzer = LLMSentimentAnalyzer(api_key="test-key")
        results = analyzer._parse_response("not valid json at all", mock_commits)

        # Should return neutral results for all commits
        assert len(results) == len(mock_commits)
        for result in results:
            assert result.sentiment == "neutral"
            assert result.confidence == 0.0
            assert result.summary == "Analysis failed"

    @pytest.mark.asyncio
    async def test_analyze_batch_success(self, mock_commits, mock_api_response):
        """Test successful batch analysis with mocked API."""
        analyzer = LLMSentimentAnalyzer(api_key="test-key")

        # Create mock response object
        mock_message = MagicMock()
        mock_message.content = mock_api_response
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        # Create mock client with chat.send_async
        mock_chat = MagicMock()
        mock_chat.send_async = AsyncMock(return_value=mock_response)
        mock_client = MagicMock()
        mock_client.chat = mock_chat

        results = await analyzer._analyze_batch(mock_client, mock_commits)

        assert len(results) == 5
        assert results[0].sentiment == "positive"

    @pytest.mark.asyncio
    async def test_full_analyze_with_mocked_client(self, mock_commits, mock_api_response):
        """Test full analyze_commits with mocked OpenRouter client."""
        # Create mock response object
        mock_message = MagicMock()
        mock_message.content = mock_api_response
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        # Create mock client with chat.send_async
        mock_chat = MagicMock()
        mock_chat.send_async = AsyncMock(return_value=mock_response)
        mock_client = MagicMock()
        mock_client.chat = mock_chat
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("crumbs.analysis.llm_sentiment.OpenRouter", return_value=mock_client):
            analyzer = LLMSentimentAnalyzer(api_key="test-key", batch_size=5)
            results = await analyzer.analyze_commits(mock_commits)

        assert len(results) == 5
        assert all(isinstance(r, SentimentResult) for r in results)

    @pytest.mark.asyncio
    async def test_handles_api_exception(self, mock_commits):
        """Test that API exceptions are handled gracefully."""
        # Create mock client that raises exception
        mock_chat = MagicMock()
        mock_chat.send_async = AsyncMock(side_effect=Exception("API Error"))
        mock_client = MagicMock()
        mock_client.chat = mock_chat
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("crumbs.analysis.llm_sentiment.OpenRouter", return_value=mock_client):
            analyzer = LLMSentimentAnalyzer(api_key="test-key", batch_size=5)
            results = await analyzer.analyze_commits(mock_commits)

        # Should return empty list when all batches fail
        assert results == []
