import json
import tempfile
import unittest
from pathlib import Path

from scripts.validate_manifests import main, validate_manifest


SHA256_A = "sha256:" + "a" * 64
SHA256_B = "sha256:" + "b" * 64
SHA512 = "sha512:" + "c" * 128

VALID = {
    "version": "1.2.3",
    "description": "Example tool",
    "homepage": "https://example.com",
    "license": "Apache-2.0",
    "url": "https://example.com/tool.zip",
    "hash": SHA256_A,
    "bin": "tool.exe",
}


class ManifestValidationTests(unittest.TestCase):
    def write_manifest(self, root: Path, manifest=VALID) -> Path:
        path = root / "tool.json"
        path.write_text(json.dumps(manifest), encoding="utf-8")
        return path

    def test_valid_top_level_download(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(validate_manifest(self.write_manifest(Path(directory))), [])

    def test_valid_architecture_downloads(self):
        manifest = VALID | {
            "architecture": {
                "32bit": {"url": "https://example.com/x86.zip", "hash": SHA256_B},
                "64bit": {"url": "https://example.com/x64.zip", "hash": SHA256_A},
                "arm64": {"url": "https://example.com/arm64.zip", "hash": SHA512},
            }
        }
        manifest.pop("url")
        manifest.pop("hash")
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(validate_manifest(self.write_manifest(Path(directory), manifest)), [])

    def test_rejects_unsupported_architecture_names(self):
        for architecture in ("amd64", "x86_64", "aarch64"):
            with self.subTest(architecture=architecture), tempfile.TemporaryDirectory() as directory:
                manifest = VALID | {
                    "architecture": {
                        architecture: {
                            "url": "https://example.com/tool.zip",
                            "hash": SHA256_A,
                        }
                    }
                }
                manifest.pop("url")
                manifest.pop("hash")

                errors = validate_manifest(self.write_manifest(Path(directory), manifest))

                self.assertTrue(
                    any(
                        f"architecture.{architecture}: unsupported architecture" in error
                        for error in errors
                    )
                )

    def test_reports_invalid_json(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "broken.json"
            path.write_text("{", encoding="utf-8")
            self.assertIn("invalid JSON", validate_manifest(path)[0])

    def test_reports_non_dict_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "list.json"
            path.write_text("[]", encoding="utf-8")
            self.assertIn("must be a JSON object", validate_manifest(path)[0])

    def test_reports_missing_contract_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            errors = validate_manifest(self.write_manifest(Path(directory), {}))
            self.assertTrue(any("missing non-empty version" in error for error in errors))
            self.assertTrue(any("expected one of" in error for error in errors))
            self.assertTrue(any("missing url" in error for error in errors))

    def test_reports_mismatched_download_lists(self):
        manifest = VALID | {"url": ["https://example.com/a.zip", "https://example.com/b.zip"], "hash": [SHA256_A]}
        with tempfile.TemporaryDirectory() as directory:
            errors = validate_manifest(self.write_manifest(Path(directory), manifest))
            self.assertTrue(any("equal length" in error for error in errors))

    def test_valid_list_urls_and_hashes(self):
        manifest = VALID | {
            "url": ["https://example.com/a.zip", "https://example.com/b.zip"],
            "hash": [SHA256_A, SHA256_B],
        }
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(validate_manifest(self.write_manifest(Path(directory), manifest)), [])

    def test_reports_invalid_url_in_list(self):
        manifest = VALID | {
            "url": ["ftp://example.com/a.zip"],
            "hash": [SHA256_A],
        }
        with tempfile.TemporaryDirectory() as directory:
            errors = validate_manifest(self.write_manifest(Path(directory), manifest))
            self.assertTrue(any("url must contain valid https URLs" in error for error in errors))

    def test_reports_invalid_url_scheme(self):
        manifest = VALID | {"url": "ftp://example.com/tool.zip"}
        with tempfile.TemporaryDirectory() as directory:
            errors = validate_manifest(self.write_manifest(Path(directory), manifest))
            self.assertTrue(any("valid https URL" in error for error in errors))

    def test_reports_http_scheme_rejected(self):
        manifest = VALID | {"url": "http://example.com/tool.zip"}
        with tempfile.TemporaryDirectory() as directory:
            errors = validate_manifest(self.write_manifest(Path(directory), manifest))
            self.assertTrue(any("valid https URL" in error for error in errors))


    def test_accepts_a_bare_sha256_digest(self):
        manifest = VALID | {"hash": "a" * 64}
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(validate_manifest(self.write_manifest(Path(directory), manifest)), [])

    def test_rejects_collision_broken_hash_algorithms(self):
        for digest in ("md5:" + "a" * 32, "sha1:" + "a" * 40):
            with self.subTest(hash=digest), tempfile.TemporaryDirectory() as directory:
                manifest = VALID | {"hash": digest}
                errors = validate_manifest(self.write_manifest(Path(directory), manifest))
                self.assertTrue(any("is not accepted" in error for error in errors))

    def test_rejects_malformed_digest_bodies(self):
        for digest in ("sha256:abc", "sha256:" + "z" * 64, "sha512:" + "a" * 64):
            with self.subTest(hash=digest), tempfile.TemporaryDirectory() as directory:
                manifest = VALID | {"hash": digest}
                errors = validate_manifest(self.write_manifest(Path(directory), manifest))
                self.assertTrue(any("hex characters" in error for error in errors))

    def test_rejects_weak_hash_in_list_and_architecture_entries(self):
        listed = VALID | {
            "url": ["https://example.com/a.zip"],
            "hash": ["md5:" + "a" * 32],
        }
        with tempfile.TemporaryDirectory() as directory:
            errors = validate_manifest(self.write_manifest(Path(directory), listed))
            self.assertTrue(any("hash[0]" in error and "is not accepted" in error for error in errors))

        per_arch = VALID | {
            "architecture": {"64bit": {"url": "https://example.com/x64.zip", "hash": "sha1:" + "a" * 40}}
        }
        per_arch.pop("url")
        per_arch.pop("hash")
        with tempfile.TemporaryDirectory() as directory:
            errors = validate_manifest(self.write_manifest(Path(directory), per_arch))
            self.assertTrue(any("architecture.64bit" in error and "is not accepted" in error for error in errors))


    def test_reports_missing_hash_and_invalid_hash(self):
        manifest_no_hash = VALID.copy()
        manifest_no_hash.pop("hash")
        with tempfile.TemporaryDirectory() as directory:
            errors = validate_manifest(self.write_manifest(Path(directory), manifest_no_hash))
            self.assertTrue(any("missing hash" in error for error in errors))

        manifest_empty_hash = VALID | {"hash": ""}
        with tempfile.TemporaryDirectory() as directory:
            errors = validate_manifest(self.write_manifest(Path(directory), manifest_empty_hash))
            self.assertTrue(any("hash must be a non-empty string" in error for error in errors))

    def test_reports_invalid_architecture_configurations(self):
        manifest_empty_arch = VALID | {"architecture": {}}
        manifest_empty_arch.pop("url")
        manifest_empty_arch.pop("hash")
        with tempfile.TemporaryDirectory() as directory:
            errors = validate_manifest(self.write_manifest(Path(directory), manifest_empty_arch))
            self.assertTrue(any("must be a non-empty object" in error for error in errors))

        manifest_invalid_arch_download = VALID | {"architecture": {"64bit": "invalid"}}
        manifest_invalid_arch_download.pop("url")
        manifest_invalid_arch_download.pop("hash")
        with tempfile.TemporaryDirectory() as directory:
            errors = validate_manifest(self.write_manifest(Path(directory), manifest_invalid_arch_download))
            self.assertTrue(any("must be an object" in error for error in errors))

    def test_validates_top_level_download_next_to_architecture(self):
        # Scoop falls back to the top-level url for an architecture the
        # manifest does not list, so that url needs the same checks.
        per_arch = {"64bit": {"url": "https://example.com/x64.zip", "hash": SHA256_A}}
        cases = {
            "valid https URL": {"url": "http://example.com/x86.zip", "hash": SHA256_B},
            "missing hash": {"url": "https://example.com/x86.zip"},
            "is not accepted": {"url": "https://example.com/x86.zip", "hash": "md5:" + "a" * 32},
            "missing url": {"hash": SHA256_B},
        }
        for expected, top_level in cases.items():
            with self.subTest(expected=expected), tempfile.TemporaryDirectory() as directory:
                manifest = {k: v for k, v in VALID.items() if k not in ("url", "hash")}
                manifest |= {"architecture": per_arch} | top_level
                errors = validate_manifest(self.write_manifest(Path(directory), manifest))
                self.assertTrue(any(expected in error for error in errors), errors)

    def test_accepts_valid_top_level_download_next_to_architecture(self):
        manifest = VALID | {
            "architecture": {"64bit": {"url": "https://example.com/x64.zip", "hash": SHA256_B}}
        }
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(validate_manifest(self.write_manifest(Path(directory), manifest)), [])

    def test_rejects_keys_scoop_reads_in_another_case(self):
        # PowerShell reads "Architecture" as "architecture"; the validator must
        # not accept a manifest whose download fields it cannot see.
        unchecked = {"64bit": {"url": "http://example.com/other.zip"}}
        cases = {
            "Architecture": VALID | {"Architecture": unchecked},
            "ARCHITECTURE": VALID | {"ARCHITECTURE": {"amd64": unchecked["64bit"]}},
            "arch\u0131tecture": VALID | {"arch\u0131tecture": unchecked},
            "URL": {k: v for k, v in VALID.items() if k not in ("url", "hash")}
            | {
                "architecture": {
                    "64bit": {
                        "url": "https://example.com/x64.zip",
                        "hash": SHA256_A,
                        "URL": "http://example.com/other.zip",
                    }
                }
            },
        }
        for key, manifest in cases.items():
            with self.subTest(key=key), tempfile.TemporaryDirectory() as directory:
                errors = validate_manifest(self.write_manifest(Path(directory), manifest))
                self.assertTrue(
                    any(f"key '{key}' must be lower-case ASCII" in error for error in errors),
                    errors,
                )

    def test_rejects_versions_that_turn_off_the_hash_check(self):
        # Scoop does not verify downloads when the version is "nightly", in
        # any letter case, so a manifest with a correct hash would install
        # unverified.
        cases = {
            "nightly": "skip the hash check",
            "Nightly": "skip the hash check",
            "NIGHTLY": "skip the hash check",
            "n\u0131ghtly": "only ASCII",
            "nightly\u200b": "only ASCII",
            "1.0 beta": "only ASCII",
        }
        for version, expected in cases.items():
            with self.subTest(version=version), tempfile.TemporaryDirectory() as directory:
                manifest = VALID | {"version": version}
                errors = validate_manifest(self.write_manifest(Path(directory), manifest))
                self.assertTrue(any(expected in error for error in errors), errors)

    def test_accepts_release_and_dated_nightly_versions(self):
        for version in ("0.10.6", "1.2.3-rc.1+build_5", "nightly-20261118"):
            with self.subTest(version=version), tempfile.TemporaryDirectory() as directory:
                manifest = VALID | {"version": version}
                self.assertEqual(validate_manifest(self.write_manifest(Path(directory), manifest)), [])

    def test_main_validates_manifests_scoop_can_find(self):
        # Scoop searches the bucket recursively and Windows ignores suffix case.
        for relative in ("nested/bad.json", "bad.JSON"):
            with self.subTest(path=relative), tempfile.TemporaryDirectory() as directory:
                bucket = Path(directory) / "bucket"
                (bucket / relative).parent.mkdir(parents=True)
                self.write_manifest(bucket, VALID)
                (bucket / relative).write_text("{}", encoding="utf-8")
                self.assertEqual(main(bucket), 1)

    def test_empty_bucket_is_valid_during_repository_bootstrap(self):
        with tempfile.TemporaryDirectory() as directory:
            bucket = Path(directory) / "bucket"
            bucket.mkdir()
            # Default allow_empty=True allows bootstrap phase
            self.assertEqual(main(bucket), 0)

    def test_empty_bucket_fails_with_forbid_empty_flag(self):
        with tempfile.TemporaryDirectory() as directory:
            bucket = Path(directory) / "bucket"
            bucket.mkdir()
            # Explicit forbid_empty=False (via allow_empty=False) fails
            self.assertEqual(main(bucket, allow_empty=False), 1)

    def test_missing_bucket_directory_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            bucket = Path(directory) / "nonexistent" / "bucket"
            # Missing directory always fails regardless of allow_empty
            self.assertEqual(main(bucket, allow_empty=True), 1)

    def test_main_validates_manifests_in_bucket_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            bucket = Path(directory) / "bucket"
            bucket.mkdir()
            self.write_manifest(bucket, VALID)
            self.assertEqual(main(bucket), 0)

    def test_main_returns_error_code_on_validation_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            bucket = Path(directory) / "bucket"
            bucket.mkdir()
            (bucket / "bad.json").write_text("{}", encoding="utf-8")
            self.assertEqual(main(bucket), 1)

    def test_validator_can_fail_on_known_bad_manifest(self):
        """Fixture test: ensure validator reports errors on invalid manifests."""
        bad_manifests = [
            ({}, "missing required fields"),
            ({"version": "1.0", "description": "Bad", "homepage": "https://example.com", "license": "MIT"}, "missing url/hash/bin"),
            (
                {
                    "version": "1.0",
                    "description": "Bad",
                    "homepage": "https://example.com",
                    "license": "MIT",
                    "url": "http://example.com/tool.zip",  # Invalid HTTP scheme
                    "hash": SHA256_A,
                    "bin": "tool.exe",
                },
                "invalid http scheme",
            ),
        ]
        for manifest, test_case in bad_manifests:
            with self.subTest(test_case=test_case), tempfile.TemporaryDirectory() as directory:
                errors = validate_manifest(self.write_manifest(Path(directory), manifest))
                self.assertGreater(len(errors), 0, f"Expected errors for {test_case}")


if __name__ == "__main__":
    unittest.main()
