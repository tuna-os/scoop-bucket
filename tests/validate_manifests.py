#!/usr/bin/env python3
"""Compatibility entry point for CI until its workflow can be updated."""

import runpy
from pathlib import Path


if __name__ == "__main__":
    runpy.run_path(
        Path(__file__).parents[1] / "scripts" / "validate_manifests.py",
        run_name="__main__",
    )
