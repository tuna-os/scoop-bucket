#!/usr/bin/env python3
"""Old path of the manifest validator, kept so existing commands still work.

The validator is scripts/validate_manifests.py. This file only runs it, with
the same arguments and exit status. Remove it when ci.yml calls the new path.
"""

import runpy
from pathlib import Path

if __name__ == "__main__":
    validator = Path(__file__).resolve().parent.parent / "scripts" / "validate_manifests.py"
    runpy.run_path(str(validator), run_name="__main__")
