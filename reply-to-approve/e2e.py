#!/usr/bin/env python3
"""One real end-to-end pass of the gate.

The gate runs as a separate process and polls a real HTTP API over a socket.
Two rounds, in the order that matters:

  1. an approver replies something unparseable  -> gate stays blocked
  2. the approver replies with the grammar      -> gate proceeds

Round 1 also proves the self-approval guard: the clarification the gate posts
contains a worked example ("go 2") on its own line and lands under the
approver's own login, so without the marker filter the gate would read its
own help text back as an approval.

Offline by default: GATE_LIVE_REPO switches this to a real GitHub issue.
"""
import json
import subprocess
import sys
import time
from datetime import timedelta

from tests.fake_github import FakeGitHub, minutes_ago

REPO = "owner/repo"
ISSUE = 7
APPROVER = "repo-owner"
EXIT = {0: "approved", 10: "skipped", 12: "timeout"}


def run_gate(api_base, opened_at, timeout, poll_interval):
    started = time.monotonic()
    proc = subprocess.run(
        [
            sys.executable, "-m", "src.gate_cli",
            "--repo", REPO,
            "--issue", str(ISSUE),
            "--approver", APPROVER,
            "--api-base", api_base,
            "--opened-at", opened_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "--timeout", str(timeout),
            "--poll-interval", str(poll_interval),
        ],
        capture_output=True,
        text=True,
    )
    elapsed = time.monotonic() - started
    return proc, elapsed


def check(label, condition, detail=""):
    print(f"  {'PASS' if condition else 'FAIL'}  {label}{detail and f' ({detail})'}")
    if not condition:
        raise SystemExit(f"end-to-end failed: {label}")


def main():
    # The gate opened a moment ago; replies arrive after it.
    opened_at = minutes_ago(1)
    results = {}

    with FakeGitHub(REPO, ISSUE, post_author=APPROVER) as gh:
        print("round 1: approver replies with something the grammar rejects")
        gh.add_comment("these all look interesting", author=APPROVER,
                       created_at=opened_at + timedelta(seconds=10))
        proc, elapsed = run_gate(gh.api_base, opened_at, timeout=4, poll_interval=2)
        blocked = json.loads(proc.stdout)

        check("gate stayed blocked", proc.returncode == 12,
              f"exit {proc.returncode} = {EXIT.get(proc.returncode)}")
        check("no decision was invented", blocked["decision"] is None)
        check("asked for clarification exactly once",
              len(gh.bodies_by(APPROVER)) == 2, "1 human reply + 1 nudge")
        check("its own worked example did not approve anything",
              blocked["outcome"] == "timeout")
        results["blocked"] = dict(blocked, elapsed_s=round(elapsed, 2))

        print("round 2: approver replies with the grammar")
        gh.add_comment("go 3 but keep it short", author=APPROVER)
        proc, elapsed = run_gate(gh.api_base, opened_at, timeout=20, poll_interval=2)
        approved = json.loads(proc.stdout)

        check("gate proceeded", proc.returncode == 0,
              f"exit {proc.returncode} = {EXIT.get(proc.returncode)}")
        check("picked the approved choice", approved["choice"] == 3,
              f"choice={approved['choice']}")
        check("kept the steering", approved["steering"] == "but keep it short")
        check("ignored the nudge's example", approved["choice"] != 2)
        results["approved"] = dict(approved, elapsed_s=round(elapsed, 2))

        results["api_calls"] = gh.get_count

    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
