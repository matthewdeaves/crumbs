"""Semantic analysis of commit messages."""

import re
from dataclasses import dataclass


@dataclass
class MessageQuality:
    """Quality metrics for a commit message."""

    is_conventional: bool
    sentiment_score: float  # -1.0 to 1.0 (negative to positive)
    specificity_score: float  # 0.0 to 1.0 (vague to precise)

    @property
    def overall_score(self) -> float:
        """Calculate overall quality score (0.0 to 1.0)."""
        # Weight: 40% conventional, 20% sentiment, 40% specificity
        conventional_weight = 0.4 if self.is_conventional else 0.0
        # Normalize sentiment from [-1, 1] to [0, 1]
        sentiment_normalized = (self.sentiment_score + 1) / 2
        sentiment_weight = sentiment_normalized * 0.2
        specificity_weight = self.specificity_score * 0.4
        return conventional_weight + sentiment_weight + specificity_weight


class SemanticAnalyzer:
    """Analyze commit message quality.

    Provides analysis of commit messages including:
    - Conventional commit format compliance
    - Sentiment scoring (positive/neutral/negative tone)
    - Specificity scoring (how precise vs vague the message is)
    """

    # Conventional commit pattern
    CONVENTIONAL_PATTERN = re.compile(
        r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)"
        r"(\([^)]+\))?:\s*.+",
        re.IGNORECASE,
    )

    # Positive sentiment indicators
    POSITIVE_WORDS = {
        "add",
        "implement",
        "create",
        "improve",
        "enhance",
        "optimize",
        "complete",
        "finish",
        "resolve",
        "fix",
        "clean",
        "simplify",
        "clarify",
        "enable",
        "support",
    }

    # Negative sentiment indicators
    NEGATIVE_WORDS = {
        "remove",
        "delete",
        "deprecate",
        "disable",
        "break",
        "fail",
        "error",
        "bug",
        "issue",
        "problem",
        "hack",
        "workaround",
        "temporary",
        "revert",
    }

    # Vague words that reduce specificity
    VAGUE_WORDS = {
        "update",
        "change",
        "modify",
        "fix",
        "stuff",
        "things",
        "misc",
        "various",
        "some",
        "minor",
        "small",
        "wip",
        "todo",
        "cleanup",
    }

    # Specific indicators that improve specificity
    SPECIFIC_PATTERNS = [
        r"\b[A-Z][a-z]+(?:[A-Z][a-z]+)+\b",  # CamelCase identifiers
        r"\b[a-z]+_[a-z]+\b",  # snake_case identifiers
        r"\b\d+\b",  # Numbers
        r"#\d+",  # Issue references
        r"\b(?:api|url|http|json|sql|css|html)\b",  # Technical terms
        r"\bfunction\b|\bmethod\b|\bclass\b|\bmodule\b",  # Code concepts
        r"\berror\s+\d+\b|\berror\s+[A-Z]+\d+\b",  # Error codes
    ]

    def check_compliance(self, message: str) -> bool:
        """Check if message follows conventional commits format.

        Args:
            message: The commit message (first line is evaluated)

        Returns:
            True if message follows conventional commits format
        """
        if not message:
            return False

        first_line = message.strip().split("\n")[0]
        return bool(self.CONVENTIONAL_PATTERN.match(first_line))

    def score_sentiment(self, message: str) -> float:
        """Score the sentiment of a commit message.

        Args:
            message: The commit message

        Returns:
            Score from -1.0 (negative) to 1.0 (positive)
        """
        if not message:
            return 0.0

        words = set(message.lower().split())

        positive_count = len(words & self.POSITIVE_WORDS)
        negative_count = len(words & self.NEGATIVE_WORDS)

        total = positive_count + negative_count
        if total == 0:
            return 0.0  # Neutral

        # Calculate score: positive pushes toward 1, negative toward -1
        return (positive_count - negative_count) / total

    def score_specificity(self, message: str) -> float:
        """Score how specific/precise a commit message is.

        Args:
            message: The commit message

        Returns:
            Score from 0.0 (vague) to 1.0 (precise)
        """
        if not message:
            return 0.0

        # Get first line for analysis
        first_line = message.strip().split("\n")[0].lower()
        words = set(first_line.split())

        # Count vague words (penalty)
        vague_count = len(words & self.VAGUE_WORDS)

        # Count specific patterns (bonus)
        specific_count = 0
        for pattern in self.SPECIFIC_PATTERNS:
            matches = re.findall(pattern, message, re.IGNORECASE)
            specific_count += len(matches)

        # Length bonus (longer messages tend to be more specific)
        # Optimal range is 50-100 chars for first line
        length = len(first_line)
        if length < 10:
            length_score = 0.0
        elif length < 50:
            length_score = length / 50.0 * 0.5
        elif length <= 100:
            length_score = 0.5
        else:
            # Penalty for very long first lines
            length_score = max(0.3, 0.5 - (length - 100) / 200)

        # Calculate base score
        base_score = 0.5

        # Apply bonuses and penalties
        specificity_bonus = min(specific_count * 0.1, 0.3)
        vague_penalty = min(vague_count * 0.1, 0.3)

        score = base_score + length_score * 0.4 + specificity_bonus - vague_penalty

        # Clamp to [0, 1]
        return max(0.0, min(1.0, score))

    def analyze(self, message: str) -> MessageQuality:
        """Perform full quality analysis on a commit message.

        Args:
            message: The commit message

        Returns:
            MessageQuality with all metrics
        """
        return MessageQuality(
            is_conventional=self.check_compliance(message),
            sentiment_score=self.score_sentiment(message),
            specificity_score=self.score_specificity(message),
        )

    def analyze_commits(self, commits: list) -> dict:
        """Analyze quality metrics for a list of commits.

        Args:
            commits: List of Commit objects

        Returns:
            Dictionary with aggregate quality metrics
        """
        if not commits:
            return {
                "total_analyzed": 0,
                "conventional_count": 0,
                "conventional_percentage": 0.0,
                "avg_sentiment": 0.0,
                "avg_specificity": 0.0,
                "avg_overall_quality": 0.0,
            }

        qualities = [self.analyze(c.message) for c in commits]

        conventional_count = sum(1 for q in qualities if q.is_conventional)
        avg_sentiment = sum(q.sentiment_score for q in qualities) / len(qualities)
        avg_specificity = sum(q.specificity_score for q in qualities) / len(qualities)
        avg_overall = sum(q.overall_score for q in qualities) / len(qualities)

        return {
            "total_analyzed": len(commits),
            "conventional_count": conventional_count,
            "conventional_percentage": conventional_count / len(commits),
            "avg_sentiment": avg_sentiment,
            "avg_specificity": avg_specificity,
            "avg_overall_quality": avg_overall,
        }
