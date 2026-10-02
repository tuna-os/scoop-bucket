# TunaOS Scoop Bucket

Scoop bucket for TunaOS tooling. The release pipelines of the upstream
repositories (for example, GoReleaser) publish the manifests.

## Currently available

This bucket has no manifests yet. It is ready, but no tool release has
published a manifest to it.

## Pending

- `bluefin-cli` (from [tuna-os/bluefin-cli](https://github.com/tuna-os/bluefin-cli))
  has no manifest here yet. Its releases ship binary assets since v0.10.6.
  The GoReleaser Scoop publisher has not made a manifest for it yet.

## Contributing manifests

Add Scoop manifests as JSON files under `bucket/`. Before you open a pull
request, run the dependency-free validator and its unit tests from the
repository root:

```console
python3 tests/validate_manifests.py
python3 -m unittest discover -s tests -v
```

See the [contribution guide](CONTRIBUTING.md) for manifest requirements,
contribution scope, and release-pipeline ownership guidance.
