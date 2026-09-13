"""The gate loop: what it takes to actually unblock the pipeline."""
import unittest
from datetime import datetime, timedelta, timezone

from src.approval_gate import MARKER, Comment, wait_for_decision
from tests.fakes import FakeClock, FakeComments

OPENED = datetime(2026, 9, 14, 8, 0, tzinfo=timezone.utc)
OWNER = "repo-owner"


def comment(body, author=OWNER, minutes=1, cid=1):
    return Comment(
        id=cid,
        author=author,
        body=body,
        created_at=OPENED + timedelta(minutes=minutes),
    )


class HappyPath(unittest.TestCase):
    def test_matching_reply_from_an_approver_unblocks(self):
        source = FakeComments([comment("go 3 but keep it short")])
        result = wait_for_decision(
            source, opened_at=OPENED, approvers=[OWNER], clock=FakeClock()
        )
        self.assertEqual(result.outcome, "approved")
        self.assertEqual(result.decision.choice, 3)
        self.assertEqual(result.decision.steering, "but keep it short")

    def test_skip_reply_rolls_over_instead_of_building(self):
        source = FakeComments([comment("skip")])
        result = wait_for_decision(
            source, opened_at=OPENED, approvers=[OWNER], clock=FakeClock()
        )
        self.assertEqual(result.outcome, "skipped")


class StaysBlocked(unittest.TestCase):
    """The only safe default: silence and noise both mean 'do not ship'."""

    def test_unparseable_reply_does_not_proceed_and_times_out(self):
        source = FakeComments([comment("these all look interesting")])
        clock = FakeClock()
        result = wait_for_decision(
            source, opened_at=OPENED, approvers=[OWNER], clock=clock, timeout=300
        )
        self.assertEqual(result.outcome, "timeout")
        self.assertIsNone(result.decision)

    def test_unparseable_reply_asks_for_clarification_exactly_once(self):
        source = FakeComments([comment("these all look interesting")])
        asked = []
        wait_for_decision(
            source,
            opened_at=OPENED,
            approvers=[OWNER],
            clock=FakeClock(),
            timeout=300,
            on_unclear=asked.append,
        )
        self.assertEqual(len(asked), 1)

    def test_no_reply_at_all_times_out(self):
        result = wait_for_decision(
            FakeComments([]), opened_at=OPENED, approvers=[OWNER],
            clock=FakeClock(), timeout=120,
        )
        self.assertEqual(result.outcome, "timeout")


class WhoIsAllowedToDecide(unittest.TestCase):
    """Each of these is a way a gate quietly opens itself if you skip it."""

    def test_a_stranger_saying_go_is_ignored(self):
        source = FakeComments([comment("go 1", author="passer-by")])
        result = wait_for_decision(
            source, opened_at=OPENED, approvers=[OWNER], clock=FakeClock(), timeout=60
        )
        self.assertEqual(result.outcome, "timeout")

    def test_the_pipeline_cannot_approve_itself(self):
        # The pipeline echoes the instruction it parsed so Tom can check it,
        # which means its own comment reads as a valid approval next round.
        own_post = f"Read your reply as:\n\ngo 3 but keep it short\n\n{MARKER}"
        source = FakeComments([comment(own_post, author=OWNER)])
        result = wait_for_decision(
            source, opened_at=OPENED, approvers=[OWNER], clock=FakeClock(), timeout=60
        )
        self.assertEqual(result.outcome, "timeout")

    def test_a_decision_from_before_the_gate_opened_is_stale(self):
        source = FakeComments([comment("go 1", minutes=-30)])
        result = wait_for_decision(
            source, opened_at=OPENED, approvers=[OWNER], clock=FakeClock(), timeout=60
        )
        self.assertEqual(result.outcome, "timeout")

    def test_approver_matching_ignores_login_case(self):
        source = FakeComments([comment("go 2", author=OWNER.upper())])
        result = wait_for_decision(
            source, opened_at=OPENED, approvers=[OWNER], clock=FakeClock()
        )
        self.assertEqual(result.outcome, "approved")


class ChangingYourMind(unittest.TestCase):
    def test_the_newest_instruction_wins(self):
        source = FakeComments(
            [comment("go 2", cid=1, minutes=1), comment("go 5", cid=2, minutes=9)]
        )
        result = wait_for_decision(
            source, opened_at=OPENED, approvers=[OWNER], clock=FakeClock()
        )
        self.assertEqual(result.decision.choice, 5)

    def test_an_unclear_reply_followed_by_a_real_one_approves(self):
        thread = [
            [comment("hmm, not sure", cid=1, minutes=1)],
            [comment("hmm, not sure", cid=1, minutes=1), comment("go 4", cid=2, minutes=6)],
        ]
        clock = FakeClock()
        result = wait_for_decision(
            source=FakeComments(thread),
            opened_at=OPENED,
            approvers=[OWNER],
            clock=clock,
            timeout=600,
            poll_interval=30,
        )
        self.assertEqual((result.outcome, result.decision.choice), ("approved", 4))
        self.assertEqual(result.polls, 2)


if __name__ == "__main__":
    unittest.main()
