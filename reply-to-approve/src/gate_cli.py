#!/usr/bin/env python3
"""The gate as a command: block until a human replies, then exit with a code.

    python3 -m src.gate_cli --repo owner/repo --issue 12 --approver owner

Exit codes are the interface, so any orchestrator can branch on them without
parsing anything:

    0   approved   -> proceed, details on stdout as JSON
    10  skipped    -> the human declined, roll over
    12  timeout    -> nobody decided; escalate, never assume
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone

from .approval_gate import MARKER, wait_for_decision
from .github_comments import ApiError, GitHubComments

EXIT_APPROVED = 0
EXIT_SKIPPED = 10
EXIT_TIMEOUT = 12
EXIT_ERROR = 2

CODES = {"approved": EXIT_APPROVED, "skipped": EXIT_SKIPPED, "timeout": EXIT_TIMEOUT}

# Note the worked example sits on its own line, which means this very comment
# parses as a valid approval. That is why the marker matters: the gate has to
# be able to recognise and skip its own writing.
NUDGE = f"""I could not read that as a decision, so nothing has been built.

Reply with a choice on its own line, for example:

go 2

or reply `skip` to roll this batch over.

{MARKER}"""


def parse_args(argv):
    p = argparse.ArgumentParser(description="Block until a human approves.")
    p.add_argument("--repo", required=True, help="owner/name")
    p.add_argument("--issue", required=True, type=int)
    p.add_argument("--approver", action="append", required=True,
                   help="GitHub login allowed to decide (repeatable)")
    p.add_argument("--api-base", default="https://api.github.com")
    p.add_argument("--token", default=os.environ.get("GITHUB_TOKEN"))
    p.add_argument("--opened-at", help="ISO timestamp; earlier replies are stale")
    p.add_argument("--timeout", type=float, default=3600.0)
    p.add_argument("--poll-interval", type=float, default=30.0)
    p.add_argument("--no-nudge", action="store_true",
                   help="do not post a clarification comment")
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv if argv is not None else sys.argv[1:])
    source = GitHubComments(args.repo, args.issue, token=args.token,
                            api_base=args.api_base)
    opened_at = (
        datetime.fromisoformat(args.opened_at)
        if args.opened_at
        else datetime.now(timezone.utc)
    )

    def on_unclear(comment):
        print(f"unclear reply from {comment.author} (comment {comment.id}): "
              "asking for clarification, not guessing", file=sys.stderr)
        if not args.no_nudge:
            source.post_comment(NUDGE)

    try:
        result = wait_for_decision(
            source,
            opened_at=opened_at,
            approvers=args.approver,
            timeout=args.timeout,
            poll_interval=args.poll_interval,
            on_unclear=on_unclear,
        )
    except ApiError as e:
        print(f"gate could not reach the API: {e}", file=sys.stderr)
        return EXIT_ERROR

    d = result.decision
    print(json.dumps({
        "outcome": result.outcome,
        "decision": d.action if d else None,
        "choice": d.choice if d else None,
        "steering": d.steering if d else None,
        "polls": result.polls,
        "comment_id": result.comment.id if result.comment else None,
    }, indent=2))
    return CODES[result.outcome]


if __name__ == "__main__":
    raise SystemExit(main())
