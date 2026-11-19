#!/usr/bin/env python3
"""Generate bucket/bluefin-cli.json from the latest bluefin-cli release.

The bucket owns its own publication (#4): this script reads the producer's
latest stable GitHub release through the public API, takes the Windows archive
hashes from the release's checksums.txt, and writes the manifest. With
--check-freshness it writes nothing and fails when the committed manifest lags
a release that is older than the allowed window, so a skipped publication
cannot stay silently green.

Standard library only, like the validator.
"""

import argparse
import json
import os
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:  # imported as scripts.update_manifest by the unit tests
    from scripts.validate_manifests import validate_manifest
except ImportError:  # run as python3 scripts/update_manifest.py
    from validate_manifests import validate_manifest


REPO_ROOT = Path(__file__).resolve().parent.parent
PACKAGE = "bluefin-cli"
PRODUCER = "tuna-os/bluefin-cli"
HOMEPAGE = f"https://github.com/{PRODUCER}"
# Kept equal to the scoops block in the producer's .goreleaser.yaml.
DESCRIPTION = (
    "Make your terminal experience awesome — shell config, tool bundles, "
    "and theming for any OS"
)
LICENSE = "Apache-2.0"
BINARY = "bluefin-cli.exe"
CHECKSUMS_ASSET = "checksums.txt"
# Scoop architecture name -> GoReleaser archive arch.
ARCHITECTURES = {"64bit": "amd64", "arm64": "arm64"}
DEFAULT_MAX_LAG = timedelta(hours=24)


class PublicationError(Exception):
    """The release does not carry what the manifest needs."""


def archive_name(version: str, arch: str) -> str:
    return f"{PACKAGE}_{version}_windows_{arch}.zip"


def parse_checksums(text: str) -> dict[str, str]:
    """Map file name to SHA-256 digest from a GoReleaser checksums.txt."""
    checksums = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) == 2:
            digest, name = parts
            checksums[name.lstrip("*")] = digest.lower()
    return checksums


def release_version(release: dict) -> str:
    tag = release.get("tag_name")
    if not isinstance(tag, str) or not tag:
        raise PublicationError("release has no tag_name")
    return tag.removeprefix("v")


def asset_url(release: dict, name: str) -> str:
    for asset in release.get("assets", []):
        if asset.get("name") == name:
            return asset["browser_download_url"]
    raise PublicationError(f"release {release.get('tag_name')} has no asset {name}")


def build_manifest(release: dict, checksums: dict[str, str]) -> dict:
    version = release_version(release)
    tag = release["tag_name"]
    architecture = {}
    autoupdate_architecture = {}
    for scoop_arch, arch in ARCHITECTURES.items():
        name = archive_name(version, arch)
        if name not in checksums:
            raise PublicationError(f"{CHECKSUMS_ASSET} has no digest for {name}")
        architecture[scoop_arch] = {
            "url": asset_url(release, name),
            "hash": checksums[name],
        }
        autoupdate_architecture[scoop_arch] = {
            "url": (
                f"{HOMEPAGE}/releases/download/"
                f"{tag.replace(version, '$version')}/{archive_name('$version', arch)}"
            )
        }
    return {
        "version": version,
        "description": DESCRIPTION,
        "homepage": HOMEPAGE,
        "license": LICENSE,
        "architecture": architecture,
        "bin": BINARY,
        "checkver": {"github": HOMEPAGE},
        "autoupdate": {
            "architecture": autoupdate_architecture,
            "hash": {"url": f"$baseurl/{CHECKSUMS_ASSET}"},
        },
    }


def freshness_error(
    manifest_path: Path, release: dict, now: datetime, max_lag: timedelta
) -> str | None:
    """Return why the manifest is stale, or None when it is fresh enough."""
    version = release_version(release)
    published = datetime.fromisoformat(release["published_at"].replace("Z", "+00:00"))
    current = None
    if manifest_path.is_file():
        current = json.loads(manifest_path.read_text(encoding="utf-8")).get("version")
    if current == version:
        return None
    lag = now - published
    if lag <= max_lag:
        return None
    hours = int(lag.total_seconds() // 3600)
    return (
        f"{manifest_path.name} is at {current or 'nothing'}, but {PRODUCER} "
        f"released {version} {hours}h ago (limit {int(max_lag.total_seconds() // 3600)}h)"
    )


def _fetch(url: str, accept: str) -> bytes:
    request = urllib.request.Request(url, headers={"Accept": accept})
    token = os.environ.get("GITHUB_TOKEN")
    if token and url.startswith("https://api.github.com/"):
        request.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def fetch_latest_release() -> dict:
    url = f"https://api.github.com/repos/{PRODUCER}/releases/latest"
    return json.loads(_fetch(url, "application/vnd.github+json"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "bucket" / f"{PACKAGE}.json",
        help="manifest path (default: bucket/bluefin-cli.json)",
    )
    parser.add_argument(
        "--check-freshness",
        action="store_true",
        help="write nothing; fail if the manifest lags the latest release too long",
    )
    parser.add_argument(
        "--max-lag-hours",
        type=float,
        default=DEFAULT_MAX_LAG.total_seconds() / 3600,
        help="allowed lag for --check-freshness (default: 24)",
    )
    args = parser.parse_args(argv)

    try:
        release = fetch_latest_release()
        if args.check_freshness:
            error = freshness_error(
                args.output,
                release,
                datetime.now(timezone.utc),
                timedelta(hours=args.max_lag_hours),
            )
            if error:
                print(f"Error: {error}", file=sys.stderr)
                return 1
            print(f"{args.output.name} is current with {PRODUCER} {release['tag_name']}.")
            return 0
        checksums_text = _fetch(asset_url(release, CHECKSUMS_ASSET), "application/octet-stream")
        manifest = build_manifest(release, parse_checksums(checksums_text.decode("utf-8")))
    except PublicationError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(manifest, indent=4, ensure_ascii=False) + "\n"
    args.output.write_text(text, encoding="utf-8")
    errors = validate_manifest(args.output)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(f"Wrote {args.output} for {PACKAGE} {manifest['version']}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
