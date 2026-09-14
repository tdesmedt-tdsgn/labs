"""A human approval gate built out of replies, not a dashboard."""
import re
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

# The pipeline stamps its own comments with this so it can never read one of
# them back as a human decision. Without it, the agent approves itself: the
# instructions it posts ("reply go N to approve") contain the grammar.
MARKER = "<!-- ctoblog-pipeline -->"

APPROVE_RE = re.compile(r"^\s*go\s+(\d+)\s*(.*)$", re.IGNORECASE)
SKIP_RE = re.compile(r"^\s*skip\s*$", re.IGNORECASE)

# Everything from here down was written by a mail client, not by the approver.
QUOTE_RE = re.compile(r"^\s*>")
ATTRIBUTION_RE = re.compile(r"^\s*On\b.*\bwrote:\s*$", re.IGNORECASE)
SIGNATURE_RE = re.compile(r"^--\s*$")


@dataclass(frozen=True)
class Decision:
    action: str  # "approve" | "skip" | "unclear"
    choice: int | None = None
    steering: str = ""


def _own_words(body: str):
    """Yield the approver's own lines, stopping at quoted or appended text."""
    for line in body.splitlines():
        if QUOTE_RE.match(line) or ATTRIBUTION_RE.match(line) or SIGNATURE_RE.match(line):
            return
        yield line


def parse_reply(body: str) -> Decision:
    """Map a comment body onto a decision. Unrecognised means unclear, and
    unclear never proceeds: the gate refuses rather than guesses."""
    for line in _own_words(body):
        m = APPROVE_RE.match(line)
        if m:
            return Decision("approve", int(m.group(1)), m.group(2).strip())
        if SKIP_RE.match(line):
            return Decision("skip")
    return Decision("unclear")


@dataclass(frozen=True)
class Comment:
    id: int
    author: str
    body: str
    created_at: datetime


@dataclass(frozen=True)
class GateResult:
    outcome: str  # "approved" | "skipped" | "timeout"
    decision: Decision | None = None
    comment: Comment | None = None
    polls: int = 0


class SystemClock:
    def now(self):
        return datetime.now(timezone.utc)

    def sleep(self, seconds):
        time.sleep(seconds)


def eligible(comments, *, opened_at, approvers):
    """Comments that are allowed to decide anything, oldest first.

    Three filters, and dropping any one of them is a way the gate opens
    itself: a stranger commenting "go 1"; the pipeline reading its own
    echoed instruction back; a decision left over from a previous round.
    """
    allowed = {a.lower() for a in approvers}
    return sorted(
        (
            c
            for c in comments
            if c.author.lower() in allowed
            and MARKER not in c.body
            and c.created_at > opened_at
        ),
        key=lambda c: c.created_at,
    )


def wait_for_decision(
    source,
    *,
    opened_at,
    approvers,
    clock=None,
    timeout=3600,
    poll_interval=30,
    on_unclear=None,
):
    """Block until an approver decides, or until the deadline.

    Returns "approved", "skipped" or "timeout". There is deliberately no
    outcome that means "probably fine": if nothing parses, the caller is left
    holding a timeout and has to escalate to a human.
    """
    clock = clock or SystemClock()
    deadline = clock.now() + timedelta(seconds=timeout)
    nudged = set()
    polls = 0

    while True:
        polls += 1
        candidates = eligible(
            source.list_comments(), opened_at=opened_at, approvers=approvers
        )
        # Newest instruction wins: if a stale round left "go 2" above a later
        # "go 5", the later one is what the approver currently means.
        for c in reversed(candidates):
            d = parse_reply(c.body)
            if d.action == "approve":
                return GateResult("approved", d, c, polls)
            if d.action == "skip":
                return GateResult("skipped", d, c, polls)

        for c in candidates:
            if c.id not in nudged:
                nudged.add(c.id)
                if on_unclear:
                    on_unclear(c)

        if clock.now() >= deadline:
            return GateResult("timeout", polls=polls)
        clock.sleep(poll_interval)
