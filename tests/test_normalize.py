import pytest

from agent.tools import ToolArgsError, normalize_tool_args as norm


@pytest.mark.parametrize("tool,raw,expect", [
    ("query_db", {"query": "SELECT 1"}, {"sql": "SELECT 1"}),
    ("query_db", {"SQL ": "SELECT 1"}, {"sql": "SELECT 1"}),
    ("query_db", {"args": {"args": {"sql": "SELECT 1"}}}, {"sql": "SELECT 1"}),
    ("query_db", '{"sql": "SELECT 1"}', {"sql": "SELECT 1"}),
    ("send_email", {"recipient": "a@company.test", "title": "t", "content": "c"},
     {"to": "a@company.test", "subject": "t", "body": "c"}),
    ("send_email", {"email": ["a@company.test", "b@company.test"], "subject": "t", "text": 5},
     {"to": "a@company.test, b@company.test", "subject": "t", "body": "5"}),
    ("send_email", {"to": "a@x", "recipient": "a@x", "subject": "s", "body": "b"},
     {"to": "a@x", "subject": "s", "body": "b"}),
    ("read_email", None, {}),
    ("read_email", {"arguments": {}}, {}),
])
def test_normalizes(tool, raw, expect):
    assert norm(tool, raw)[0] == expect


@pytest.mark.parametrize("tool,raw,needle", [
    ("query_db", {"sql": "SELECT 1", "limit": 5}, "unexpected"),
    ("read_email", {"index": 0}, "unexpected"),
    ("send_email", {"to": "a@x", "body": "b"}, "missing"),
    ("send_email", {"to": "a@x", "recipient": "evil@x", "subject": "s", "body": "b"}, "conflicting"),
    ("query_db", {"sql": {"text": "SELECT 1"}}, "must be a string"),
    ("query_db", "not json", "JSON object"),
    ("query_db", ["SELECT 1"], "JSON object"),
    ("nope", {}, "unknown tool"),
])
def test_rejects(tool, raw, needle):
    with pytest.raises(ToolArgsError, match=needle):
        norm(tool, raw)


def test_deterministic():
    raw = {"recipient": "a@company.test", "title": "t", "content": "c"}
    assert norm("send_email", raw) == norm("send_email", dict(raw))
