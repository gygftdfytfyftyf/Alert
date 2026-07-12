from __future__ import annotations

from bot.services.member_resolve import parse_member_tokens


def test_parse_member_tokens_multiline() -> None:
    text = "@alice\nbob, 12345\n@carol;"
    assert parse_member_tokens(text) == ["@alice", "bob", "12345", "@carol"]


def test_parse_member_tokens_empty_lines() -> None:
    assert parse_member_tokens("  \n  ") == []
