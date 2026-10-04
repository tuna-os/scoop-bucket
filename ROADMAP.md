# Scoop Bucket Roadmap

**Last updated:** 2026-10-04  
**Owner:** tuna-os  
**Mission:** Give Windows users a verified, current package-manager path to
TunaOS command-line tools.

## Current state (Q4 2026 checkpoint)

**Status**: Channel launch gates defined (Q3 close); no manifests published yet.
Producer readiness complete: `bluefin-cli` ships amd64/arm64 Windows archives 
with checksums since v0.10.6. **Blocker**: credential provisioning and manifest 
validation automation remain unstarted (5+ weeks since gate definition). No
clear owner assigned; work is sequenced but not staffed.

The repository itself is CI-mature: manifest validator runs on PR, STE checks 
pass, and least-privilege workflow permissions are set. The bucket is ready to
receive submissions; the publication pipeline is not.

Near-term objective: prove one complete install-and-update loop for 
`bluefin-cli` with documented ownership and failure signals reusable by later 
producers.

## Near term: launch the channel (Q4 2026)

| Outcome | Evidence required | Tracking | Status | Age |
| --- | --- | --- | --- | --- |
| **BLOCKER**: Name bucket publication owner and credential model | Owner identity, least-privilege token scope, and producer/consumer contract | #4 | 🔴 Unstarted | 36d |
| Cut & publish first `bluefin-cli` manifest | Manifest on `main` passes validation, targets stable amd64+arm64 Windows archives | #14 | 🔴 Blocked on #4 | 36d |
| Verify install + update | Clean amd64 Windows: `scoop bucket add`, `scoop install bluefin-cli`, `bluefin-cli --version` | #14 | 🔴 Blocked on manifest | 36d |
| Publish release-drift detection | Upstream release older than 24 hours without matching manifest triggers owner alert | #4, #14 | 🔴 Unstarted | 36d |

## Mid term: operate a dependable channel

After the launch evidence is recorded:

- Keep each declared stable package within 24 hours of its upstream release.
- Verify manifest URLs, hashes, architectures, and a clean install before
  promotion.
- Document rollback for a bad manifest and retain the prior working version.
- Review channel health monthly: package count, stale packages, failed
  publications, and verified installs.
- Admit another producer only after the `bluefin-cli` publication contract has
  survived at least two consecutive stable releases.

## Definition of healthy

The channel is healthy when it has at least one installable package, every
declared package matches an upstream stable release within 24 hours, and a
failed or skipped publication cannot remain silently green.

## Strategic risk

The 36-day gap between gate definition and zero progress signals either a
staffing shortage or a sequencing mismatch. Both are recoverable:

- **Staffing**: the manifest author path is clear (see #14 for specifics);
one owner + one afternoon → first manifest.
- **Sequencing**: #4 ownership decision is genuinely unblocking — decide it,
and #14 becomes a straightforward automation task.

No architectural risk; no unknown unknowns. The risk is pure execution.

## Governance

Roadmap status changes must link to verifiable artifacts such as a manifest,
an upstream release, an automated freshness result, or an install transcript.
Technical implementation belongs in the relevant issue or pull request; this
document records user-visible outcomes and sequencing.

---
*Maintained by the strategist agent (ACMM L6 — full mode). Last refresh: 2026-10-04.*
