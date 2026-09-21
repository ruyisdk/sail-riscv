#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Run the matrix-multiply generator suite from the canonical Ztt test runner.

``gen/tests`` is the canonical entry point (``python3 -m tests``); this module
delegates to ``mmul_gen/tests`` so a single command covers both generators.
"""

from __future__ import annotations

from pathlib import Path


MMUL_GEN_TESTS = Path(__file__).resolve().parents[1] / "mmul_gen" / "tests"


def load_tests(loader, tests, pattern):  # noqa: ANN001 - unittest protocol
    return loader.discover(
        start_dir=str(MMUL_GEN_TESTS),
        pattern="test_*.py",
        top_level_dir=str(MMUL_GEN_TESTS.parents[1]),
    )
