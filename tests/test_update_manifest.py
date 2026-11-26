import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts.update_manifest import (
    PublicationError,
    build_manifest,
    freshness_error,
    parse_checksums,
)
from scripts.validate_manifests import validate_manifest


BASE = "https://github.com/tuna-os/bluefin-cli/releases/download/v1.2.3"
AMD64 = "bluefin-cli_1.2.3_windows_amd64.zip"
ARM64 = "bluefin-cli_1.2.3_windows_arm64.zip"
CHECKSUMS = (
    f"{'a' * 64}  {AMD64}\n"
    f"{'b' * 64}  {ARM64}\n"
    f"{'c' * 64}  bluefin-cli-plus_1.2.3_windows_amd64.zip\n"
    f"{'d' * 64}  bluefin-cli_1.2.3_linux_amd64.tar.gz\n"
)
PUBLISHED = datetime(2026, 11, 18, 12, 0, tzinfo=timezone.utc)


def release(**overrides):
    names = [AMD64, ARM64, "checksums.txt", "bluefin-cli-plus_1.2.3_windows_amd64.zip"]
    return {
        "tag_name": "v1.2.3",
        "published_at": PUBLISHED.isoformat().replace("+00:00", "Z"),
        "assets": [{"name": name, "browser_download_url": f"{BASE}/{name}"} for name in names],
    } | overrides


class BuildManifestTests(unittest.TestCase):
    def test_standard_windows_archives_with_release_digests(self):
        manifest = build_manifest(release(), parse_checksums(CHECKSUMS))
        self.assertEqual(manifest["version"], "1.2.3")
        self.assertEqual(
            manifest["architecture"],
            {
                "64bit": {"url": f"{BASE}/{AMD64}", "hash": "a" * 64},
                "arm64": {"url": f"{BASE}/{ARM64}", "hash": "b" * 64},
            },
        )
        self.assertEqual(manifest["bin"], "bluefin-cli.exe")

    def test_autoupdate_templates_follow_the_release_layout(self):
        autoupdate = build_manifest(release(), parse_checksums(CHECKSUMS))["autoupdate"]
        self.assertEqual(
            autoupdate["architecture"]["64bit"]["url"],
            "https://github.com/tuna-os/bluefin-cli/releases/download/"
            "v$version/bluefin-cli_$version_windows_amd64.zip",
        )
        self.assertEqual(autoupdate["hash"], {"url": "$baseurl/checksums.txt"})

    def test_generated_manifest_passes_the_validator(self):
        manifest = build_manifest(release(), parse_checksums(CHECKSUMS))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bluefin-cli.json"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            self.assertEqual(validate_manifest(path), [])

    def test_missing_digest_is_an_error_not_an_unpinned_download(self):
        checksums = parse_checksums(CHECKSUMS)
        del checksums[ARM64]
        with self.assertRaisesRegex(PublicationError, ARM64):
            build_manifest(release(), checksums)

    def test_missing_asset_is_an_error(self):
        assets = [asset for asset in release()["assets"] if asset["name"] != AMD64]
        with self.assertRaisesRegex(PublicationError, AMD64):
            build_manifest(release(assets=assets), parse_checksums(CHECKSUMS))

    def test_checksums_accept_binary_mode_marker(self):
        self.assertEqual(parse_checksums(f"{'A' * 64} *{AMD64}\n"), {AMD64: "a" * 64})


class FreshnessTests(unittest.TestCase):
    def check(self, current_version, age, releases=None):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bluefin-cli.json"
            if current_version is not None:
                path.write_text(json.dumps({"version": current_version}), encoding="utf-8")
            return freshness_error(
                path, releases or [release()], PUBLISHED + age, timedelta(hours=24)
            )

    def test_matching_version_is_fresh_however_old(self):
        self.assertIsNone(self.check("1.2.3", timedelta(days=30)))

    def test_lag_inside_window_is_tolerated(self):
        self.assertIsNone(self.check("1.2.2", timedelta(hours=23)))

    def test_lag_past_window_fails(self):
        error = self.check("1.2.2", timedelta(hours=25))
        self.assertIn("1.2.2", error)
        self.assertIn("1.2.3 25h ago", error)

    def test_missing_manifest_past_window_fails(self):
        self.assertIn("at nothing", self.check(None, timedelta(hours=25)))

    def test_old_unpublished_release_fails_despite_fresh_latest(self):
        older = release(tag_name="v1.2.2", published_at="2026-11-15T12:00:00Z")
        newest = release(published_at="2026-11-18T10:00:00Z")
        error = self.check(None, timedelta(hours=0), [newest, older])
        self.assertIn("1.2.2", error)
        self.assertIn("2 release(s)", error)

    def test_only_fresh_release_unpublished_is_tolerated(self):
        older = release(tag_name="v1.2.2", published_at="2026-11-15T12:00:00Z")
        newest = release(published_at="2026-11-18T10:00:00Z")
        self.assertIsNone(self.check("1.2.2", timedelta(hours=0), [newest, older]))


if __name__ == "__main__":
    unittest.main()
