"""Tests for commit message parser."""

import pytest

from crumbs.git.parser import CommitMessageParser, ParsedMessage
from crumbs.models import CommitType


@pytest.fixture
def parser():
    """Create a parser instance."""
    return CommitMessageParser()


class TestParseConventionalCommits:
    """Tests for parsing conventional commit format."""

    def test_feat_with_scope(self, parser):
        """Parse feat(scope): subject format."""
        result = parser.parse("feat(auth): add login functionality")

        assert result.commit_type == CommitType.FEAT
        assert result.scope == "auth"
        assert result.subject == "add login functionality"
        assert result.is_conventional is True

    def test_fix_without_scope(self, parser):
        """Parse fix: subject format."""
        result = parser.parse("fix: resolve memory leak")

        assert result.commit_type == CommitType.FIX
        assert result.scope is None
        assert result.subject == "resolve memory leak"
        assert result.is_conventional is True

    def test_docs_with_scope(self, parser):
        """Parse docs(readme): subject format."""
        result = parser.parse("docs(readme): update installation steps")

        assert result.commit_type == CommitType.DOCS
        assert result.scope == "readme"
        assert result.subject == "update installation steps"
        assert result.is_conventional is True

    def test_all_commit_types(self, parser):
        """Test all conventional commit types are recognized."""
        types = [
            ("feat", CommitType.FEAT),
            ("fix", CommitType.FIX),
            ("docs", CommitType.DOCS),
            ("style", CommitType.STYLE),
            ("refactor", CommitType.REFACTOR),
            ("perf", CommitType.PERF),
            ("test", CommitType.TEST),
            ("build", CommitType.BUILD),
            ("ci", CommitType.CI),
            ("chore", CommitType.CHORE),
            ("revert", CommitType.REVERT),
        ]

        for type_str, expected_type in types:
            result = parser.parse(f"{type_str}: test message")
            assert result.commit_type == expected_type, f"Failed for {type_str}"
            assert result.is_conventional is True

    def test_case_insensitive(self, parser):
        """Parser should handle uppercase types."""
        result = parser.parse("FEAT(auth): add feature")

        assert result.commit_type == CommitType.FEAT
        assert result.is_conventional is True

    def test_mixed_case(self, parser):
        """Parser should handle mixed case types."""
        result = parser.parse("Feat(Auth): Add Feature")

        assert result.commit_type == CommitType.FEAT
        assert result.scope == "Auth"
        assert result.is_conventional is True


class TestParseNonConventional:
    """Tests for non-conventional commit messages."""

    def test_simple_message(self, parser):
        """Non-conventional messages should have UNKNOWN type."""
        result = parser.parse("quick fix for login")

        assert result.commit_type == CommitType.UNKNOWN
        assert result.scope is None
        assert result.subject == "quick fix for login"
        assert result.is_conventional is False

    def test_unknown_type(self, parser):
        """Unknown type should result in UNKNOWN CommitType."""
        result = parser.parse("foo: this is not a valid type")

        assert result.commit_type == CommitType.UNKNOWN
        assert result.is_conventional is False

    def test_missing_colon(self, parser):
        """Message without colon is not conventional."""
        result = parser.parse("feat add new feature")

        assert result.commit_type == CommitType.UNKNOWN
        assert result.is_conventional is False

    def test_empty_message(self, parser):
        """Empty message should return defaults."""
        result = parser.parse("")

        assert result.commit_type == CommitType.UNKNOWN
        assert result.scope is None
        assert result.subject == ""
        assert result.is_conventional is False

    def test_whitespace_only(self, parser):
        """Whitespace-only message should return defaults."""
        result = parser.parse("   \n\t  ")

        assert result.commit_type == CommitType.UNKNOWN
        assert result.subject == ""
        assert result.is_conventional is False


class TestParseBody:
    """Tests for parsing commit body."""

    def test_message_with_body(self, parser):
        """Extract body from multi-line message."""
        message = """feat(auth): add login

This implements the OAuth2 flow for user authentication.
It supports Google and GitHub providers."""

        result = parser.parse(message)

        assert result.commit_type == CommitType.FEAT
        assert result.subject == "add login"
        assert "OAuth2 flow" in result.body
        assert "Google and GitHub" in result.body

    def test_message_without_body(self, parser):
        """Single-line message has no body."""
        result = parser.parse("fix: quick fix")

        assert result.body is None

    def test_body_with_trailers(self, parser):
        """Body should not include trailers."""
        message = """feat(auth): add login

Implemented OAuth2.

Co-Authored-By: Claude <claude@anthropic.com>"""

        result = parser.parse(message)

        assert "Implemented OAuth2" in result.body
        assert "Co-Authored-By" not in result.body


class TestExtractCoAuthors:
    """Tests for co-author extraction."""

    def test_single_co_author(self, parser):
        """Extract single co-author."""
        message = """feat: add feature

Co-Authored-By: Claude <claude@anthropic.com>"""

        co_authors = parser.extract_co_authors(message)

        assert len(co_authors) == 1
        assert "Claude <claude@anthropic.com>" in co_authors[0]

    def test_multiple_co_authors(self, parser):
        """Extract multiple co-authors."""
        message = """feat: add feature

Co-Authored-By: Alice <alice@example.com>
Co-Authored-By: Bob <bob@example.com>"""

        co_authors = parser.extract_co_authors(message)

        assert len(co_authors) == 2
        assert any("Alice" in ca for ca in co_authors)
        assert any("Bob" in ca for ca in co_authors)

    def test_no_co_authors(self, parser):
        """Message without co-authors returns empty list."""
        message = "feat: add feature"

        co_authors = parser.extract_co_authors(message)

        assert co_authors == []

    def test_case_insensitive_co_author(self, parser):
        """Co-author header is case-insensitive."""
        message = """feat: add feature

co-authored-by: Claude <claude@anthropic.com>"""

        co_authors = parser.extract_co_authors(message)

        assert len(co_authors) == 1

    def test_empty_message(self, parser):
        """Empty message returns empty list."""
        assert parser.extract_co_authors("") == []
        assert parser.extract_co_authors(None) == []


class TestDetectPhase:
    """Tests for phase detection."""

    def test_phase_in_subject(self, parser):
        """Detect phase in subject line."""
        message = "feat: Phase 3 - add authentication"

        phase = parser.detect_phase(message)

        assert phase == 3

    def test_phase_in_body(self, parser):
        """Detect phase in message body."""
        message = """feat: add feature

This is part of Phase 5 implementation."""

        phase = parser.detect_phase(message)

        assert phase == 5

    def test_no_phase(self, parser):
        """Message without phase returns None."""
        message = "feat: add feature without phase reference"

        phase = parser.detect_phase(message)

        assert phase is None

    def test_case_insensitive_phase(self, parser):
        """Phase detection is case-insensitive."""
        assert parser.detect_phase("PHASE 1 start") == 1
        assert parser.detect_phase("phase 2 work") == 2
        assert parser.detect_phase("Phase 10 final") == 10

    def test_first_phase_wins(self, parser):
        """If multiple phases, return first one."""
        message = "Phase 1 and Phase 2 work"

        phase = parser.detect_phase(message)

        assert phase == 1

    def test_empty_message(self, parser):
        """Empty message returns None."""
        assert parser.detect_phase("") is None
        assert parser.detect_phase(None) is None
