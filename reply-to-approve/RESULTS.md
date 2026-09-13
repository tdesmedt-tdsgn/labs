# Results

Every number the post quotes comes from this file. Reproduce with
`./verify.sh` (offline) or the live command at the bottom.

Run date: 2026-09-14. Python 3.12.7, macOS arm64. No third-party packages.

## Step 1 — unit tests

```
step 1/3: unit tests (grammar, gate loop, GitHub adapter over real HTTP)
----------------------------------------------------------------------
Ran 27 tests in 2.546s

OK
```

27 tests. The ~2.5s is almost entirely the adapter tests, which start real
HTTP servers; the grammar and gate-loop tests run on a virtual clock and take
under a millisecond in total.

## Step 2 — offline end-to-end

The gate runs as a separate process (`python3 -m src.gate_cli`) and polls a
local GitHub-shaped HTTP server over a socket.

```
round 1: approver replies with something the grammar rejects
  PASS  gate stayed blocked (exit 12 = timeout)
  PASS  no decision was invented
  PASS  asked for clarification exactly once (1 human reply + 1 nudge)
  PASS  its own worked example did not approve anything
round 2: approver replies with the grammar
  PASS  gate proceeded (exit 0 = approved)
  PASS  picked the approved choice (choice=3)
  PASS  kept the steering
  PASS  ignored the nudge's example
{
  "blocked": {
    "outcome": "timeout",
    "decision": null,
    "choice": null,
    "steering": null,
    "polls": 3,
    "comment_id": null,
    "elapsed_s": 4.09
  },
  "approved": {
    "outcome": "approved",
    "decision": "approve",
    "choice": 3,
    "steering": "but keep it short",
    "polls": 1,
    "comment_id": 1003,
    "elapsed_s": 0.09
  },
  "api_calls": 4
}
```

Measured:

| What | Value |
|---|---|
| Blocked round: polls before giving up | 3 (2s interval, 4s timeout) |
| Blocked round: wall clock | 4.09 s |
| Blocked round: exit code | 12 (timeout) |
| Clarification comments posted | 1, for 1 unparseable reply |
| Approved round: polls needed | 1 |
| Approved round: wall clock | 0.09 s |
| Approved round: exit code | 0 |
| Total API calls across both rounds | 4 |

The blocked round is the one that matters: an approver did reply, the reply
was friendly, and the pipeline still shipped nothing.

## Step 3 — live pass against api.github.com

Read-only, against the real ideas issue that approved this very post
(`tdesmedt-tdsgn/CTOBlog` issue 1). No comments posted.

```
step 3/3: live pass against api.github.com
          repo=tdesmedt-tdsgn/CTOBlog issue=1 (read-only, no comments posted)
{
  "outcome": "approved",
  "decision": "approve",
  "choice": 3,
  "steering": "",
  "polls": 1,
  "comment_id": 5656544412
}
live pass: the gate read a real human decision off a real issue
verify.sh: OK
```

The decision it read, `go 3`, is the approval that commissioned this post.
The thread also contained a bot comment; the author and marker filters
excluded it, and one poll was enough.

Command used:

```bash
GITHUB_TOKEN="$(gh auth token)" \
GATE_LIVE_REPO="tdesmedt-tdsgn/CTOBlog" \
GATE_LIVE_ISSUE=1 \
GATE_LIVE_APPROVER="tdesmedt-tdsgn" \
GATE_LIVE_SINCE="2026-09-01T00:00:00Z" \
./verify.sh
```

CI has no token, so CI runs steps 1 and 2 only and says so in its output.

## Size

```
$ grep -vE '^\s*(#|$)' src/approval_gate.py | wc -l
97
```

97 non-blank, non-comment lines for the whole gate — grammar, eligibility
filters and polling loop, including docstrings. The grammar itself is two
regular expressions. The GitHub adapter is a further 50 lines and the CLI
wrapper 75.

## What is not measured here

- No load or concurrency testing. One gate, one issue, one approver.
- The adapter reads a single page of 100 comments; a longer thread would
  need Link-header pagination.
- "Ask for clarification once" holds within one gate process. A restarted
  gate will nudge again, because nothing is persisted.
- The live pass reads an issue that was already approved. It proves the
  adapter and the filters against real GitHub payloads; it does not
  re-test the blocking path live, which the offline round does.
