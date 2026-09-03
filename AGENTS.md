# AGENTS.md — agent guide for tuna-os/scoop-bucket

The **Scoop bucket** for TunaOS command-line tools: the repository a Windows
user adds with `scoop bucket add tuna-os https://github.com/tuna-os/scoop-bucket`.

Human docs: [`README.md`](README.md), [`CONTRIBUTING.md`](CONTRIBUTING.md)
(manifest requirements), [`ROADMAP.md`](ROADMAP.md) (what "healthy" means here).

## The bucket is empty, and that makes CI vacuous

There is **no `bucket/` directory** — not one manifest has been published yet.
`main()` in `tests/validate_manifests.py` treats that as success:

```python
manifests = sorted(bucket.glob("*.json")) if bucket.is_dir() else []
if not manifests:
    print("No manifests published yet; nothing to validate.")
    return 0
```

So `ci.yml`'s **"Validate published manifests" step passes without validating
anything.** The only check with teeth today is the second step, the validator's
own 15-test unit suite. A green tick on this repo currently means "the
validator's tests pass", not "the bucket is good" — and the ROADMAP's stated
health bar is precisely that "a failed or skipped publication cannot remain
silently green". Do not treat CI here as evidence about published packages
until `bucket/` actually has contents.

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
- **Standard library only, by design.** `ci.yml` has no `pip install` step; a
  dependency added here breaks the workflow rather than being auto-installed.
- **URLs must be `https://`.** `_is_valid_url` is a literal
  `url.startswith("https://")` — plain `http` is rejected, not warned about.
- Architecture-specific downloads are validated per architecture, and paired
  `url`/`hash` lists must have equal length.

## Configured but unenforced

```bash
python3 tests/validate_manifests.py     # vacuous while bucket/ is absent
python3 -m unittest discover -s tests   # 15 tests
ruff check .                            # config in ruff.toml; clean on main
```

> `ruff.toml` sets the lint rules and `codecov.yml` sets a 45% project coverage
> target, but **`ci.yml` runs neither** — no ruff step, no coverage upload. The
> tree happens to be ruff-clean right now, so wiring it in is cheap; the
> coverage gate cannot report at all until something uploads coverage.
