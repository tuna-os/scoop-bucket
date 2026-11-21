#!/usr/bin/env python3
"""Validate the repository's Scoop manifests without external dependencies."""

import json
import sys
from pathlib import Path


REQUIRED_FIELDS = ("version", "description", "homepage", "license")
INSTALL_FIELDS = ("bin", "shortcuts", "installer")
SUPPORTED_ARCHITECTURES = frozenset({"32bit", "64bit", "arm64"})
# Scoop verifies a download with the algorithm named by the hash prefix, and
# with SHA-256 when the digest carries no prefix. Only the two collision-
# resistant algorithms are accepted here: a manifest pinned with md5: or sha1:
# would install under an algorithm an attacker can forge a collision for.
HASH_DIGEST_LENGTHS = {"sha256": 64, "sha512": 128}
HEX_DIGITS = set("0123456789abcdefABCDEF")
VERSION_CHARACTERS = set(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-+_"
)


def _key_errors(fields: dict, location: str) -> list[str]:
    # Scoop is PowerShell, which matches a key without regard to case: it reads
    # "Architecture" or "URL" as the lower-case field. This validator matches
    # exact names, so a key in another case would be installed from and never
    # checked. Non-ASCII letters are refused for the same reason: some of them
    # upper-case to an ASCII letter.
    return [
        f"{location}: key '{key}' must be lower-case ASCII"
        for key in fields
        if not key.isascii() or key != key.lower()
    ]


def _version_error(version: object, location: str) -> str | None:
    # Scoop turns the hash check off when the version is "nightly" (compared
    # without regard to case): the pinned digest stays in the manifest and is
    # never used. Scoop itself accepts only word characters and ".-+_" in a
    # version; the ASCII subset is required here so that no other spelling can
    # compare equal to "nightly" in PowerShell and not in this check.
    if not isinstance(version, str) or not version:
        return None  # reported as a missing required field
    if not version.isascii() or not set(version) <= VERSION_CHARACTERS:
        return f"{location}: version may contain only ASCII letters, digits and . - + _"
    if version.lower() == "nightly":
        return f"{location}: version 'nightly' makes Scoop skip the hash check"
    return None


def _is_valid_url(url: str) -> bool:
    return isinstance(url, str) and url.startswith("https://")


def _hash_error(digest: object, location: str) -> str | None:
    if not isinstance(digest, str) or not digest:
        return f"{location}: hash must be a non-empty string"
    algorithm, separator, body = digest.rpartition(":")
    algorithm = algorithm.lower() if separator else "sha256"
    length = HASH_DIGEST_LENGTHS.get(algorithm)
    if length is None:
        accepted = ", ".join(sorted(HASH_DIGEST_LENGTHS))
        return f"{location}: hash algorithm '{algorithm}' is not accepted; use {accepted}"
    if len(body) != length or not set(body) <= HEX_DIGITS:
        return f"{location}: hash must be {length} hex characters for {algorithm}"
    return None


def validate_download(download: dict, location: str) -> list[str]:
    errors: list[str] = []
    url = download.get("url")
    digest = download.get("hash")
    if url is None:
        return [f"{location}: missing url"]
    if digest is None:
        return [f"{location}: missing hash"]
    if isinstance(url, list):
        if not url or not all(_is_valid_url(item) for item in url):
            errors.append(f"{location}: url must contain valid https URLs")
        if not isinstance(digest, list) or len(url) != len(digest):
            errors.append(f"{location}: url and hash lists must have equal length")
        else:
            errors.extend(
                error
                for index, item in enumerate(digest)
                if (error := _hash_error(item, f"{location} hash[{index}]"))
            )
        return errors
    if not _is_valid_url(url):
        errors.append(f"{location}: url must be a valid https URL or list")
    # Checked even when the URL is already rejected: both halves of the
    # integrity contract should be reported in one run, not one per fix.
    error = _hash_error(digest, location)
    if error:
        errors.append(error)
    return errors


def validate_manifest(path: Path) -> list[str]:
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return [f"{path}: invalid JSON: {error}"]

    if not isinstance(manifest, dict):
        return [f"{path}: manifest must be a JSON object"]

    errors = [
        f"{path}: missing non-empty {field}"
        for field in REQUIRED_FIELDS
        if not isinstance(manifest.get(field), str) or not manifest[field]
    ]
    if not any(field in manifest for field in INSTALL_FIELDS):
        errors.append(f"{path}: expected one of {', '.join(INSTALL_FIELDS)}")

    errors.extend(_key_errors(manifest, str(path)))
    if error := _version_error(manifest.get("version"), str(path)):
        errors.append(error)

    architecture = manifest.get("architecture")
    # Scoop reads url and hash from the architecture entry first and from the
    # top level second. A top-level download next to `architecture` is the one
    # an unlisted architecture installs, so it is checked whenever it is there.
    if architecture is None or "url" in manifest or "hash" in manifest:
        errors.extend(validate_download(manifest, str(path)))
    if architecture is None:
        return errors
    if not isinstance(architecture, dict) or not architecture:
        errors.append(f"{path}: architecture must be a non-empty object")
    else:
        for name, download in architecture.items():
            if name not in SUPPORTED_ARCHITECTURES:
                accepted = ", ".join(sorted(SUPPORTED_ARCHITECTURES))
                errors.append(
                    f"{path} architecture.{name}: unsupported architecture; use {accepted}"
                )
            if not isinstance(download, dict):
                errors.append(f"{path} architecture.{name}: must be an object")
            else:
                errors.extend(_key_errors(download, f"{path} architecture.{name}"))
                errors.extend(
                    validate_download(download, f"{path} architecture.{name}")
                )
    return errors


def main(bucket: Path = Path("bucket"), allow_empty: bool = True) -> int:
    # Resolve bucket path against repository root, not the current working directory.
    # This prevents the validator from being pointed at nothing by accident.
    repo_root = Path(__file__).parent.parent
    bucket = bucket if bucket.is_absolute() else repo_root / bucket
    
    if not bucket.is_dir():
        print(f"Error: bucket directory not found: {bucket}", file=sys.stderr)
        return 1
    
    # Scoop finds a manifest in any subdirectory of the bucket, and Windows
    # matches the .json suffix without regard to case.
    manifests = sorted(
        path
        for path in bucket.rglob("*")
        if path.is_file() and path.suffix.lower() == ".json"
    )
    if not manifests:
        if allow_empty:
            print("No manifests published yet; nothing to validate.")
            return 0
        else:
            print(f"Error: no manifests found in {bucket}", file=sys.stderr)
            return 1

    errors = [error for path in manifests for error in validate_manifest(path)]
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(f"Validated {len(manifests)} manifest(s).")
    return 0


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Validate Scoop manifests")
    parser.add_argument(
        "--bucket",
        type=Path,
        default=Path("bucket"),
        help="Path to manifests directory (default: bucket/)",
    )
    parser.add_argument(
        "--forbid-empty",
        action="store_true",
        help="Fail if bucket is empty (default: allow empty during bootstrap)",
    )
    args = parser.parse_args()
    raise SystemExit(main(args.bucket, allow_empty=not args.forbid_empty))
