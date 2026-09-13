# reply-to-approve

Keeping a human in the loop on an autonomous pipeline usually gets scoped as a
review dashboard: a queue, a UI, notifications, an audit trail, a sprint or
three. This demo is the cheap version that covers most of the value. The agent
opens a GitHub issue, then blocks until someone allowed to decide replies with
a recognised instruction. Replying to the notification email counts, so the
approver never opens a new tool. The checkpoint is auditable by construction,
because the decision is a comment with an author and a timestamp.

The interesting part is not the happy path. It is what happens when the reply
does not parse, which is most of the time in practice.

## Quickstart

```bash
./verify.sh          # unit tests + one real end-to-end pass, no install needed
```

Python 3.12, standard library only. To watch a gate block and then open
against a real issue:

```bash
python3 -m src.gate_cli --repo owner/name --issue 12 --approver owner \
  --timeout 600 --poll-interval 15
```

Exit codes are the interface, so an orchestrator can branch without parsing
anything: `0` approved, `10` the human declined, `12` nobody decided in time.
There is deliberately no code that means "probably fine".

## What it proves

| Claim | Where |
|---|---|
| A friendly but unparseable reply does not ship anything | `e2e.py` round 1 |
| The gate asks for clarification once instead of guessing | `e2e.py` round 1 |
| A recognised reply unblocks, steering text intact | `e2e.py` round 2 |
| A stranger's "go 1" is ignored | `tests/test_gate.py` |
| The pipeline cannot approve itself | `tests/test_gate.py` |
| A decision from a previous round is stale, not valid | `tests/test_gate.py` |
| Quoted email history cannot approve anything | `tests/test_grammar.py` |

That fifth row is the one that bites. A pipeline posting with the owner's own
personal access token comments *as the owner*, so filtering by author is not
enough: its own help text ("reply with a choice, for example: `go 2`") reads
back as a valid approval. Every comment the pipeline writes carries an HTML
marker, and the gate skips anything carrying it. `e2e.py` reproduces exactly
this trap and asserts the gate does not fall into it.

## Layout

```
src/approval_gate.py    grammar + eligibility filters + polling loop (no GitHub)
src/github_comments.py  the only GitHub-specific code: read comments, post one
src/gate_cli.py         the gate as a command, exit codes as the interface
e2e.py                  gate as a subprocess against a real HTTP API
tests/fake_github.py    a real HTTP server speaking GitHub's comment payloads
```

`approval_gate.py` never imports the GitHub adapter. Swap in a Slack or IMAP
source and the gate logic does not change.

## Offline by default, live on request

`verify.sh` needs no credentials: the end-to-end round runs against a local
HTTP server that speaks GitHub's comment payloads, so CI gets a meaningful
green. Set `GATE_LIVE_REPO`, `GATE_LIVE_ISSUE`, `GATE_LIVE_APPROVER` and
`GITHUB_TOKEN` and `verify.sh` adds a read-only pass against api.github.com.
Measured output from both, including one live run, is in
[RESULTS.md](RESULTS.md).

## Known limits

Single page of 100 comments, no pagination. "Ask once" holds within one gate
process, because nothing is persisted across restarts. Polling, not webhooks,
which is the right trade at this scale and the wrong one at a thousand gates.

From the post:
<https://tdesmedt-tdsgn.github.io/2026/09/14/reply-to-approve.html>

MIT licensed. Part of [Tom De Smedt's](https://tdesmedt-tdsgn.github.io)
weekly build-and-write practice.
