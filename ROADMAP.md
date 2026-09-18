# Scoop Bucket Roadmap

**Last updated:** 2026-09-17  
**Owner:** tuna-os  
**Mission:** Give Windows users a verified, current package-manager path to
TunaOS command-line tools.

## Current state

The Scoop bucket is initialized and validation tooling (`tests/validate_manifests.py`)
is active in CI. The near-term objective is proving the first complete install-and-update
loop for `bluefin-cli` (Windows amd64 and arm64), establishing automated release freshness
monitoring, and expanding Scoop distribution to additional TunaOS CLI tools (`finupdate`, `wootc`).

## Near term: launch the channel (September 2026 Checkpoint)

| Outcome | Evidence required | Tracking | Status |
| --- | --- | --- | --- |
| Decide bucket publication ownership and credential model | Named owner, least-privilege write identity, and producer/consumer failure contract documented | #4 | In Progress |
| Publish the first `bluefin-cli` manifest | Manifest on `main` targets the current stable Windows amd64 and arm64 assets and passes repository validation | #14 | In Progress |
| Verify the user journey | Clean Windows amd64 run completes `scoop bucket add`, `scoop install bluefin-cli`, and `bluefin-cli --version` | #14 | Open |
| Make release drift visible | A declared stable upstream release older than 24 hours without a matching manifest produces an owner-visible failure | #4, #14 | Open |

## Mid term: operate a dependable multi-producer channel (Q4 2026)

After the launch evidence is recorded:

- Keep each declared stable package within 24 hours of its upstream release.
- Verify manifest URLs, hashes, architectures, and a clean install before promotion.
- Expand Scoop bucket manifests to secondary TunaOS tools (`finupdate`, `wootc`) once `bluefin-cli` has survived two consecutive stable releases.
- Implement automated upstream release drift monitoring and failure notification across all published manifests.
- Document rollback procedures for bad manifests and retain prior working versions.
- Review channel health monthly: package count, stale packages, failed publications, and verified installs.

## Definition of healthy

The channel is healthy when it has at least one installable package, every declared package matches an upstream stable release within 24 hours, and a failed or skipped publication cannot remain silently green.

## Governance

Roadmap status changes must link to verifiable artifacts such as a manifest, an upstream release, an automated freshness result, or an install transcript. Technical implementation belongs in the relevant issue or pull request; this document records user-visible outcomes and sequencing.
