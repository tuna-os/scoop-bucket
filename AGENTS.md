# AGENTS.md — agent guide for tuna-os/scoop-bucket

The **Scoop bucket** for TunaOS command-line tools: the repository a Windows
user adds with `scoop bucket add tuna-os https://github.com/tuna-os/scoop-bucket`.

Human docs: [`README.md`](README.md), [`CONTRIBUTING.md`](CONTRIBUTING.md)
(manifest requirements), [`ROADMAP.md`](ROADMAP.md) (what "healthy" means here).

## The bucket is empty, and that makes CI vacuous

`bucket/` holds only `.gitkeep`. Not one manifest has been published yet.
`main()` in `tests/validate_manifests.py` resolves `bucket/` against the
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

Manifests are meant to be written by the producing tool's release pipeline
(GoReleaser in the upstream repo), not by hand here. `CONTRIBUTING.md` says a
hand edit to a generated manifest is overwritten by the next release, and that
is the failure mode to avoid: the fix for a wrong version or hash almost always
belongs in the upstream `.goreleaser.yaml`, not in this repo.

`bluefin-cli` is the first declared producer and is still unpublished — its
release job skips Scoop publication when the producer-local credential is
absent, which is why the bucket is empty despite Windows assets existing since
v0.10.6.

## Validator conventions worth keeping

- **It lives in `tests/`** (`tests/validate_manifests.py`), which is unusual —
  it is both the tool CI runs against `bucket/` and the subject of
  `tests/test_validate_manifests.py`.
- **Standard library for validator.** The validator and its unit tests use only
  the Python standard library. CI separately installs coverage for its coverage
  gate; keep dependencies out of the validator itself.
- **URLs must be `https://`.** `_is_valid_url` is a literal
  `url.startswith("https://")` — plain `http` is rejected, not warned about.
- Architecture-specific downloads are validated per architecture, and paired
  `url`/`hash` lists must have equal length.

## Configured checks

```bash
python3 tests/validate_manifests.py     # vacuous while bucket/ is empty
python3 -m unittest discover -s tests   # validator unit tests
ruff check .                            # lint configured in ruff.toml
```

`ruff.toml` sets the lint rules and `codecov.yml` records a 45% project
coverage target. `ci.yml` runs Ruff and enforces that target with coverage.py;
it does not upload results because neither this repository nor the
organization has a `CODECOV_TOKEN` secret. The tree is currently Ruff-clean,
but local `ruff check .` still matters because it mirrors the CI lint gate.
