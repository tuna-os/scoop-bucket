#!/usr/bin/env python3
"""Compatibility shim -- the real validator moved to scripts/validate_manifests.py.

Temporary: .github/workflows/ci.yml still invokes this path and
`unittest discover -s tests` still imports this module name. Loaded by file
path (not `sys.path` insertion) to avoid a same-name circular import between
this shim and the real module. Both need to move to
scripts/validate_manifests.py + PYTHONPATH=scripts (tracked in the issue this
shim links back to); this file can be deleted once that lands.
"""

import importlib.util
from pathlib import Path

_real_path = Path(__file__).resolve().parent.parent / "scripts" / "validate_manifests.py"
_spec = importlib.util.spec_from_file_location("_scoop_validate_manifests_real", _real_path)
_real = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_real)

main = _real.main
validate_manifest = _real.validate_manifest

if __name__ == "__main__":
    raise SystemExit(main())
