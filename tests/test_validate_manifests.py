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


    def test_empty_bucket_is_valid_during_repository_bootstrap(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(main(Path(directory)), 0)


if __name__ == "__main__":
    unittest.main()
