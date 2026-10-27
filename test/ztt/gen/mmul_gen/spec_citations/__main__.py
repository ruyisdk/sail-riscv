#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""``python3 -B -m mmul_gen.spec_citations``: the gate's own command line."""

from __future__ import annotations

import sys

from mmul_gen.spec_citations.cli import main

if __name__ == "__main__":
    sys.exit(main())
