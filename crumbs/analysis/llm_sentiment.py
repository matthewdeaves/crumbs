"""Async LLM-based sentiment analysis using OpenRouter API."""

import asyncio
import json
import re
from typing import TYPE_CHECKING

from openrouter import OpenRouter

from crumbs.config import (
    OPENROUTER_API_KEY,
    OPENROUTER_MODEL,
    SENTIMENT_BATCH_SIZE,
)
from crumbs.models import SentimentResult

if TYPE_CHECKING:
    from crumbs.models import Commit


SENTIMENT_PROMPT = """Analyze the sentiment of these git commit messages. For each commit, determine:
1. sentiment: "positive", "neutral", or "negative"
2. confidence: 0.0 to 1.0 (how confident you are)
3. tone: a single word describing the tone (e.g., "enthusiastic", "frustrated", "routine", "celebratory", "apologetic")
4. summary: a brief 5-10 word interpretation of the commit's intent

Respond with a JSON array, one object per commit in the same order.

Commit messages:
{messages}

Respond ONLY with valid JSON array, no markdown or explanation:
[{{"sha": "...", "sentiment": "...", "confidence": 0.0, "tone": "...", "summary": "..."}}]"""


class LLMSentimentAnalyzer:
    """Async batched sentiment analysis via OpenRouter."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        batch_size: int | None = None,
    ):
        """Initialize the analyzer.

        Args:
            api_key: OpenRouter API key (defaults to env var)
            model: Model to use (defaults to env var or claude-3-haiku)
            batch_size: Commits per API call (defaults to env var or 5)
        """
        self.api_key = api_key or OPENROUTER_API_KEY
        self.model = model or OPENROUTER_MODEL
        self.batch_size = batch_size or SENTIMENT_BATCH_SIZE
        self.available = bool(self.api_key)

    async def analyze_commits(
        self, commits: list["Commit"]
    ) -> list[SentimentResult]:
        """Analyze all commits in batches asynchronously.

        Args:
            commits: List of Commit objects to analyze

        Returns:
            List of SentimentResult objects (empty if no API key)
        """
        if not self.available:
            return []

        if not commits:
            return []

        # Split into batches
        batches = [
            commits[i : i + self.batch_size]
            for i in range(0, len(commits), self.batch_size)
        ]

        results: list[SentimentResult] = []

        async with OpenRouter(api_key=self.api_key) as client:
            tasks = [self._analyze_batch(client, batch) for batch in batches]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            for batch_result in batch_results:
                if isinstance(batch_result, Exception):
                    # Log error but continue with other batches
                    continue
                results.extend(batch_result)

        return results

    async def _analyze_batch(
        self, client: OpenRouter, commits: list["Commit"]
    ) -> list[SentimentResult]:
        """Analyze a single batch of commits.

        Args:
            client: OpenRouter client
            commits: Batch of commits to analyze

        Returns:
            List of SentimentResult objects
        """
        # Build message list for prompt
        messages_text = "\n".join(
            f"[{c.sha[:8]}] {c.message.split(chr(10))[0]}" for c in commits
        )

        prompt = SENTIMENT_PROMPT.format(messages=messages_text)

        response = await client.chat.send_async(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
        )

        # Parse the response
        content = response.choices[0].message.content
        return self._parse_response(content, commits)

    def _parse_response(
        self, content: str, commits: list["Commit"]
    ) -> list[SentimentResult]:
        """Parse LLM response into SentimentResult objects.

        Args:
            content: Raw LLM response text
            commits: Original commits (for SHA fallback)

        Returns:
            List of SentimentResult objects
        """
        results = []

        # Try to extract JSON from response
        try:
            # Handle potential markdown code blocks
            json_match = re.search(r"\[.*\]", content, re.DOTALL)
            if json_match:
                content = json_match.group()

            parsed = json.loads(content)

            if not isinstance(parsed, list):
                parsed = [parsed]

            for i, item in enumerate(parsed):
                # Get SHA from response or fallback to commit
                sha = item.get("sha", commits[i].sha[:8] if i < len(commits) else "unknown")

                results.append(
                    SentimentResult(
                        sha=sha,
                        sentiment=item.get("sentiment", "neutral"),
                        confidence=float(item.get("confidence", 0.5)),
                        tone=item.get("tone", "unknown"),
                        summary=item.get("summary", ""),
                    )
                )

        except (json.JSONDecodeError, KeyError, IndexError):
            # If parsing fails, return neutral results for all commits
            for commit in commits:
                results.append(
                    SentimentResult(
                        sha=commit.sha[:8],
                        sentiment="neutral",
                        confidence=0.0,
                        tone="unknown",
                        summary="Analysis failed",
                    )
                )

        return results


def analyze_commits_sync(commits: list["Commit"]) -> list[SentimentResult]:
    """Synchronous wrapper for analyze_commits.

    Args:
        commits: List of Commit objects to analyze

    Returns:
        List of SentimentResult objects
    """
    analyzer = LLMSentimentAnalyzer()
    return asyncio.run(analyzer.analyze_commits(commits))
