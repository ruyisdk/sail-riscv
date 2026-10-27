#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""One scalar shift amount applied to every element.

Spec:    instructions.adoc:5055-5057 (msll.ew.x)
Quote:   "The shift amount is a fixed-type unsigned control scalar, does not read CSR[amestype], and is reduced modulo the ms2 element width."
Checks:  one scalar amount one past the element width must be reduced modulo the width for every element

The amount is one past the element width, which is the smallest amount the
hardware must reduce modulo the width.
"""

from __future__ import annotations

from mmul_gen.templates.integer_shift_common import IntegerShiftTemplate


class ShiftScalarSource(IntegerShiftTemplate):
    """One scalar shift amount applied to every element."""

    name = "shift_scalar_source"

    scalar_amount = True


__all__ = ["ShiftScalarSource"]
