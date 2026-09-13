# labs

Working code behind [Tom De Smedt's blog](https://tdesmedt-tdsgn.github.io).
Every post ships with a runnable, CI-verified demo — one folder per post.

## How to run any demo

```bash
cd <demo-folder>
./verify.sh
```

`verify.sh` is the contract: it sets up, runs the tests, and does one real
end-to-end pass. If it exits 0, the demo works. CI runs exactly this script
for every changed demo, so the badge on a folder means it ran, not that
someone claims it ran.

Demos that call paid APIs read keys from the environment (e.g.
`ANTHROPIC_API_KEY`) and fall back to a clearly-labeled mock mode without
one, so `verify.sh` always has a meaningful green.

## Index

| Demo | Post | One-liner |
|---|---|---|
| _(first demo lands with the first post)_ | | |

## Why this exists

Writing about engineering without shipping code is theater. Each demo is
small on purpose: it proves the one claim its post makes, nothing more.
Code is MIT-licensed — lift anything you like.

*Something here relevant to your organisation? → tom@tdsgn.be*
