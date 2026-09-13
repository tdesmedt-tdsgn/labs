# _template

Convention for every demo in this repo (copy this folder as a starting
point; the leading underscore keeps it at the top and out of the way):

```
<slug>/
  README.md      what it proves (business framing first), quickstart, post link
  verify.sh      THE contract: setup + tests + one real end-to-end pass, exit 0 = works
  RESULTS.md     actual output/metrics from a real run — the only numbers a post may quote
  src/ tests/    keep it minimal; the demo proves ONE claim
```

Rules:
- `verify.sh` needs no arguments and no pre-existing state.
- Paid APIs: read keys from env, degrade to a labeled mock mode without them.
- Small beats clever. A reader should grok the whole demo in 10 minutes.
