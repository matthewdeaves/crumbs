"""Commit message parser for conventional commits."""

import re
from dataclasses import dataclass
from typing import Optional

from crumbs.models import CommitType


@dataclass
class ParsedMessage:
    """Result of parsing a commit message."""

    commit_type: CommitType
    scope: Optional[str]
    subject: str
    body: Optional[str]
    is_conventional: bool


class CommitMessageParser:
    """Parser for conventional commit messages.

    Parses messages in the format: type(scope): subject

    Examples:
        feat(auth): add login functionality
        fix: resolve memory leak
        docs(readme): update installation steps
    """

    # Pattern for conventional commit format: type(scope): subject
    CONVENTIONAL_PATTERN = re.compile(
        r"^(?P<type>[a-z]+)"  # type (lowercase)
        r"(?:\((?P<scope>[^)]+)\))?"  # optional scope in parentheses
        r":\s*"  # colon and optional whitespace
        r"(?P<subject>.+)$",  # subject (rest of first line)
        re.IGNORECASE,
    )

    # Pattern for Co-Authored-By trailer
    CO_AUTHOR_PATTERN = re.compile(
        r"^Co-Authored-By:\s*(.+)$",
        re.IGNORECASE | re.MULTILINE,
    )

    # Pattern for phase references (Phase 1, Phase 2, etc.)
    PHASE_PATTERN = re.compile(
        r"Phase\s+(\d+)",
        re.IGNORECASE,
    )

    # Map of type strings to CommitType enum
    TYPE_MAP = {
        "feat": CommitType.FEAT,
        "fix": CommitType.FIX,
        "docs": CommitType.DOCS,
        "style": CommitType.STYLE,
        "refactor": CommitType.REFACTOR,
        "perf": CommitType.PERF,
        "test": CommitType.TEST,
        "build": CommitType.BUILD,
        "ci": CommitType.CI,
        "chore": CommitType.CHORE,
        "revert": CommitType.REVERT,
    }

    def parse(self, message: str) -> ParsedMessage:
        """Parse a commit message into its components.

        Args:
            message: The full commit message

        Returns:
            ParsedMessage with type, scope, subject, body, and conventional flag
        """
        if not message or not message.strip():
            return ParsedMessage(
                commit_type=CommitType.UNKNOWN,
                scope=None,
                subject="",
                body=None,
                is_conventional=False,
            )

        lines = message.strip().split("\n")
        first_line = lines[0].strip()

        # Try to match conventional commit format
        match = self.CONVENTIONAL_PATTERN.match(first_line)

        if match:
            type_str = match.group("type").lower()
            commit_type = self.TYPE_MAP.get(type_str, CommitType.UNKNOWN)
            scope = match.group("scope")
            subject = match.group("subject").strip()
            is_conventional = commit_type != CommitType.UNKNOWN
        else:
            commit_type = CommitType.UNKNOWN
            scope = None
            subject = first_line
            is_conventional = False

        # Extract body (everything after first line, excluding trailers)
        body = None
        if len(lines) > 1:
            # Skip empty line after subject if present
            body_lines = []
            started = False
            for line in lines[1:]:
                # Skip initial empty lines
                if not started and not line.strip():
                    continue
                # Stop at trailers (lines starting with key: value pattern at end)
                if self.CO_AUTHOR_PATTERN.match(line):
                    break
                started = True
                body_lines.append(line)

            # Remove trailing empty lines
            while body_lines and not body_lines[-1].strip():
                body_lines.pop()

            if body_lines:
                body = "\n".join(body_lines)

        return ParsedMessage(
            commit_type=commit_type,
            scope=scope,
            subject=subject,
            body=body,
            is_conventional=is_conventional,
        )

    def extract_co_authors(self, message: str) -> list[str]:
        """Extract co-authors from commit message trailers.

        Args:
            message: The full commit message

        Returns:
            List of co-author strings (e.g., ["Name <email@example.com>"])
        """
        if not message:
            return []

        matches = self.CO_AUTHOR_PATTERN.findall(message)
        return [match.strip() for match in matches]

    def detect_phase(self, message: str) -> Optional[int]:
        """Detect phase reference in commit message.

        Args:
            message: The full commit message

        Returns:
            Phase number if found, None otherwise
        """
        if not message:
            return None

        match = self.PHASE_PATTERN.search(message)
        if match:
            return int(match.group(1))
        return None
