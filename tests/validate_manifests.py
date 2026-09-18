#!/usr/bin/env python3
"""Validate the repository's Scoop manifests without external dependencies."""

import json
import sys
from pathlib import Path


REQUIRED_FIELDS = ("version", "description", "homepage", "license")
INSTALL_FIELDS = ("bin", "shortcuts", "installer")
# Scoop verifies a download with the algorithm named by the hash prefix, and
# with SHA-256 when the digest carries no prefix. Only the two collision-
# resistant algorithms are accepted here: a manifest pinned with md5: or sha1:
# would install under an algorithm an attacker can forge a collision for.
HASH_DIGEST_LENGTHS = {"sha256": 64, "sha512": 128}
HEX_DIGITS = set("0123456789abcdefABCDEF")


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

    architecture = manifest.get("architecture")
    if architecture is None:
        errors.extend(validate_download(manifest, str(path)))
    elif not isinstance(architecture, dict) or not architecture:
        errors.append(f"{path}: architecture must be a non-empty object")
    else:
        for name, download in architecture.items():
            if not isinstance(download, dict):
                errors.append(f"{path} architecture.{name}: must be an object")
            else:
                errors.extend(
                    validate_download(download, f"{path} architecture.{name}")
                )
    return errors


def main(bucket: Path = Path("bucket")) -> int:
    manifests = sorted(bucket.glob("*.json")) if bucket.is_dir() else []
    if not manifests:
        print("No manifests published yet; nothing to validate.")
        return 0

    errors = [error for path in manifests for error in validate_manifest(path)]
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(f"Validated {len(manifests)} manifest(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
