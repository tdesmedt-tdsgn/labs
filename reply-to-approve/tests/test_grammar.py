"""The approval grammar: what counts as a decision, and what does not."""
import unittest

from src.approval_gate import parse_reply


class ParseApproval(unittest.TestCase):
    def test_go_with_number_approves_that_choice(self):
        d = parse_reply("go 3")
        self.assertEqual(d.action, "approve")
        self.assertEqual(d.choice, 3)
        self.assertEqual(d.steering, "")

    def test_trailing_text_is_kept_as_steering(self):
        d = parse_reply("go 2 but shorter, focus on cost")
        self.assertEqual((d.action, d.choice), ("approve", 2))
        self.assertEqual(d.steering, "but shorter, focus on cost")

    def test_skip_rolls_the_batch_over(self):
        self.assertEqual(parse_reply("skip").action, "skip")

    def test_grammar_is_case_insensitive(self):
        self.assertEqual(parse_reply("GO 1").choice, 1)
        self.assertEqual(parse_reply("Skip").action, "skip")


class RejectAmbiguity(unittest.TestCase):
    """Anything the grammar does not recognise must never proceed."""

    def test_praise_is_not_approval(self):
        self.assertEqual(parse_reply("these all look great").action, "unclear")

    def test_go_without_a_number_is_unclear(self):
        self.assertEqual(parse_reply("go ahead").action, "unclear")

    def test_empty_body_is_unclear(self):
        self.assertEqual(parse_reply("").action, "unclear")


class EmailReplies(unittest.TestCase):
    """Replying to the notification email is the point, so the gate has to
    survive what mail clients add: greetings, signatures, quoted history."""

    def test_decision_can_sit_below_a_greeting(self):
        d = parse_reply("Morning,\n\ngo 4\n\nTom")
        self.assertEqual((d.action, d.choice), ("approve", 4))

    def test_quoted_original_message_is_ignored(self):
        body = (
            "go 2\n"
            "\n"
            "On Mon, 14 Sep 2026 at 08:02, Tom <tom@example.com> wrote:\n"
            "> Reply go N to approve a pitch\n"
            "> ## 1. Some other pitch\n"
        )
        d = parse_reply(body)
        self.assertEqual((d.action, d.choice), ("approve", 2))

    def test_a_decision_only_inside_quoted_text_does_not_count(self):
        body = (
            "Not sure yet.\n"
            "\n"
            "On Mon, 14 Sep 2026 at 08:02, Tom <tom@example.com> wrote:\n"
            "> go 1\n"
        )
        self.assertEqual(parse_reply(body).action, "unclear")

    def test_first_decision_line_wins_over_later_lines(self):
        self.assertEqual(parse_reply("go 2\ngo 5").choice, 2)


if __name__ == "__main__":
    unittest.main()
