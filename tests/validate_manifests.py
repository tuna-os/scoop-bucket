#!/usr/bin/env python3
"""Validate the repository's Scoop manifests without external dependencies."""

import json
import sys
from pathlib import Path


REQUIRED_FIELDS = ("version", "description", "homepage", "license")
INSTALL_FIELDS = ("bin", "shortcuts", "installer")


def validate_download(download: dict, location: str) -> list[str]:
    errors: list[str] = []
    url = download.get("url")
    digest = download.get("hash")
    if url is None:
        return [f"{location}: missing url"]
    if digest is None:
        return [f"{location}: missing hash"]
    if isinstance(url, list):
        if not url or not all(isinstance(item, str) and item for item in url):
            errors.append(f"{location}: url must contain non-empty strings")
        if not isinstance(digest, list) or len(url) != len(digest):
            errors.append(f"{location}: url and hash lists must have equal length")
    elif not isinstance(url, str) or not url:
        errors.append(f"{location}: url must be a non-empty string or list")
    elif not isinstance(digest, str) or not digest:
        errors.append(f"{location}: hash must be a non-empty string")
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
