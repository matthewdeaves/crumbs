"""Semantic analysis of commit messages."""


class SemanticAnalyzer:
    """Analyze commit message quality."""

    def check_compliance(self, message: str):
        """Check if message follows conventional commits."""
        raise NotImplementedError("Will be implemented in Session 3")

    def score_sentiment(self, message: str):
        """Score the sentiment of a message."""
        raise NotImplementedError("Will be implemented in Session 3")

    def score_specificity(self, message: str):
        """Score how specific/precise a message is."""
        raise NotImplementedError("Will be implemented in Session 3")
