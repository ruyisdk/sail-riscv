#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Canonical entry point for the matrix-multiply generator test suite.

Run from the generator root::

    cd sail-ame/test/ztt/gen
    python3 -m mmul_gen.tests
"""

from __future__ import annotations

from pathlib import Path
import sys
import unittest

# Allow ``python3 mmul_gen/tests/__main__.py`` in addition to ``-m``.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def main() -> int:
    tests_dir = Path(__file__).resolve().parent
    suite = unittest.defaultTestLoader.discover(
        start_dir=str(tests_dir),
        pattern="test_*.py",
        top_level_dir=str(tests_dir.parents[1]),
    )
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
