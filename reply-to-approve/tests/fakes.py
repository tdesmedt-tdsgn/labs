"""Test doubles: a virtual clock and a stand-in for the comments endpoint.

Both exist so the loop's real timing logic can be tested in milliseconds
instead of minutes. The gate code under test is the production code.
"""
from datetime import datetime, timedelta, timezone

START = datetime(2026, 9, 14, 8, 0, tzinfo=timezone.utc)


class FakeClock:
    """Sleeping advances virtual time instead of wasting real time."""

    def __init__(self, start=START):
        self.t = start
        self.slept = 0.0

    def now(self):
        return self.t

    def sleep(self, seconds):
        self.t += timedelta(seconds=seconds)
        self.slept += seconds


class FakeComments:
    """Pass a flat list for a thread that never changes, or a list of rounds
    to script what each successive poll sees."""

    def __init__(self, script):
        self.script = script
        self.polls = 0

    def list_comments(self):
        self.polls += 1
        if self.script and isinstance(self.script[0], list):
            return list(self.script[min(self.polls - 1, len(self.script) - 1)])
        return list(self.script)
