# AGENTS.md — agent guide for tuna-os/scoop-bucket

The **Scoop bucket** for TunaOS command-line tools: the repository a Windows
user adds with `scoop bucket add tuna-os https://github.com/tuna-os/scoop-bucket`.

Human docs: [`README.md`](README.md), [`CONTRIBUTING.md`](CONTRIBUTING.md)
(manifest requirements), [`ROADMAP.md`](ROADMAP.md) (what "healthy" means here).

## The bucket is empty, and that makes CI vacuous

`bucket/` holds only `.gitkeep`. Not one manifest has been published yet.
`main()` in `scripts/validate_manifests.py` resolves `bucket/` against the
repository root, not the current directory, and handles the two cases
differently:

- **Missing `bucket/` directory: failure** (exit 1, "bucket directory not
  found"). Do not delete `bucket/.gitkeep`, or the "Validate published
  manifests" step in `ci.yml` goes red.
- **Empty `bucket/`: success** ("No manifests published yet; nothing to
  validate."), unless you pass `--forbid-empty`. `ci.yml` does not pass that
  flag yet, because the bucket is still in bootstrap.

So the "Validate published manifests" step **passes without validating
anything** today. The only check with teeth is the next step, the validator's
own unit suite. A green tick on this repo currently means "the validator's
tests pass", not "the bucket is good". The ROADMAP health bar is exactly that
"a failed or skipped publication cannot remain silently green". Do not treat
CI here as evidence about published packages until `bucket/` has manifests.
When the first manifest lands, add `--forbid-empty` to that CI step so that an
emptied bucket fails.

## This is a publish target, not a source of truth

The bucket owns its publication (maintainer ruling on #4). Manifests are
generated from the producer's release, not written by hand:
`scripts/update_manifest.py` reads the latest stable `bluefin-cli` release
through the public GitHub API, takes the Windows amd64/arm64 archive digests
from that release's `checksums.txt`, writes `bucket/bluefin-cli.json`
(with `checkver`/`autoupdate`), and runs the validator on the result. It needs
no cross-repository credential; `GITHUB_TOKEN`, when set, only raises the API
rate limit. A release missing an archive or its digest is an error, never an
unpinned download.

`python3 scripts/update_manifest.py --check-freshness` writes nothing and
exits 1 when the committed manifest is behind a release older than 24 hours
(`--max-lag-hours` changes the window). That is the ROADMAP's "release drift
is visible" signal.

`.github/workflows/publish-manifests.yml` (#116) runs both modes every six
hours and on manual dispatch. It regenerates the manifest, validates it with
`--forbid-empty`, and opens a `publish/bluefin-cli-<version>` PR when
`bucket/` changed. The run fails when the manifest on `main` lags a release
by more than 24 hours, so merge that PR. The next run overwrites a hand
edit to `bucket/bluefin-cli.json`, so fix the generator or the upstream
release instead.

`bluefin-cli`'s `.goreleaser.yaml` still declares a `scoops:` publisher that
skips itself while its producer-local `SCOOP_BUCKET_TOKEN` is absent. It is a
dormant second writer; do not configure that token.

## Validator conventions worth keeping

- **It lives in `scripts/`** (`scripts/validate_manifests.py`). It is the tool
  that checks `bucket/`, and `tests/test_validate_manifests.py` tests it.
  The old `tests/validate_manifests.py` shim is gone; `ci.yml` calls the
  `scripts/` path directly.
- **Standard library for validator.** The validator and its unit tests use only
  the Python standard library. CI separately installs coverage for its coverage
  gate; keep dependencies out of the validator itself.
- **URLs must be `https://`.** `_is_valid_url` is a literal
  `url.startswith("https://")` — plain `http` is rejected, not warned about.
- Architecture-specific downloads are validated per architecture, and paired
  `url`/`hash` lists must have equal length.

## Configured checks

```bash
python3 scripts/validate_manifests.py   # vacuous while bucket/ is empty
python3 -m unittest discover -s tests   # validator unit tests
ruff check .                            # lint configured in ruff.toml
```

`ruff.toml` sets the lint rules and `codecov.yml` records a 45% project
coverage target. `ci.yml` runs Ruff and enforces that target with coverage.py;
it does not upload results because neither this repository nor the
organization has a `CODECOV_TOKEN` secret. The tree is currently Ruff-clean,
but local `ruff check .` still matters because it mirrors the CI lint gate.

`ci.yml` is not the only gate. Two more workflows check pull requests:

- `actions-security.yml` runs on every PR: `gh actions-lock --verify` against
  `.github/workflows/actions.lock`, and `zizmor` over the workflows. A
  workflow change that adds or moves a `uses:` pin must update `actions.lock`
  in the same PR.
- `ste.yml` ("Prose") runs on `**.md`, `**.mdx`, `.ste-budget` and itself. It
  calls the shared `tuna-os/.github` STE linter, which checks `README.md` and
  `CONTRIBUTING.md` (not `AGENTS.md` or `ROADMAP.md`) against `.ste-budget`.
  The budget is `0`, so any new finding in those files fails the PR. Reproduce
  from this repo's root with a `tuna-os/.github` checkout:
  `node <path-to-.github>/.github/actions/ste-lint/ste-lint.mjs --summary`.

`drop-bot-review-requests.yml` removes auto-requested reviewers from
bot-authored PRs. It does not check content.
