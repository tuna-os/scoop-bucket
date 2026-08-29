# TunaOS Scoop Bucket

Scoop bucket for TunaOS tooling. Manifests are published from the upstream
repos' release pipelines (e.g. GoReleaser).

## Currently available

No manifests are published yet — the bucket is initialized and waiting for
tool releases to ship assets.

## Pending

- `bluefin-cli` (from [tuna-os/bluefin-cli](https://github.com/tuna-os/bluefin-cli))
  is not yet published here — releases ship binary assets since v0.10.6, but
  the GoReleaser Scoop publisher has not produced a manifest yet.

## Contributing manifests

Add Scoop manifests as JSON files under `bucket/`. Before opening a pull
request, run the dependency-free validator and its unit tests from the
repository root:

```console
python3 tests/validate_manifests.py
python3 -m unittest discover -s tests -v
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for manifest requirements, contribution
scope, and release-pipeline ownership guidance.
