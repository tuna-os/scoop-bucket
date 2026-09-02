import json
import tempfile
import unittest
from pathlib import Path

from validate_manifests import main, validate_manifest


VALID = {
    "version": "1.2.3",
    "description": "Example tool",
    "homepage": "https://example.com",
    "license": "Apache-2.0",
    "url": "https://example.com/tool.zip",
    "hash": "sha256:abc",
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
                "64bit": {"url": "https://example.com/x64.zip", "hash": "abc"},
                "arm64": {"url": "https://example.com/arm64.zip", "hash": "def"},
            }
        }
        manifest.pop("url")
        manifest.pop("hash")
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(validate_manifest(self.write_manifest(Path(directory), manifest)), [])

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
        manifest = VALID | {"url": ["https://example.com/a.zip", "https://example.com/b.zip"], "hash": ["abc"]}
        with tempfile.TemporaryDirectory() as directory:
            errors = validate_manifest(self.write_manifest(Path(directory), manifest))
            self.assertTrue(any("equal length" in error for error in errors))

    def test_valid_list_urls_and_hashes(self):
        manifest = VALID | {
            "url": ["https://example.com/a.zip", "https://example.com/b.zip"],
            "hash": ["sha256:abc", "sha256:def"],
        }
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(validate_manifest(self.write_manifest(Path(directory), manifest)), [])

    def test_reports_invalid_url_in_list(self):
        manifest = VALID | {
            "url": ["ftp://example.com/a.zip"],
            "hash": ["sha256:abc"],
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

    def test_empty_bucket_is_valid_during_repository_bootstrap(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(main(Path(directory)), 0)

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


if __name__ == "__main__":
    unittest.main()

