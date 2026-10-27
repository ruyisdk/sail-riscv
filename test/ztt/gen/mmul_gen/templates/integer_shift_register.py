#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Per-element shift amounts read from a second M operand.

Spec:    instructions.adoc:5020-5021 (msll.ew)
Quote:   "Each shift amount is interpreted as an unsigned raw bit pattern and reduced modulo the ms1 element width."
Checks:  a second M operand supplies one amount per element, so the modulo reduction is pinned element by element

The amount square walks the boundary amounts, so consecutive elements pin
down the modulo reduction instead of repeating one sampled amount.
"""

from __future__ import annotations

from mmul_gen.templates.integer_shift_common import IntegerShiftTemplate


class ShiftRegisterSource(IntegerShiftTemplate):
    """Per-element shift amounts read from a second M operand."""

    name = "shift_register_source"

    scalar_amount = False


__all__ = ["ShiftRegisterSource"]
