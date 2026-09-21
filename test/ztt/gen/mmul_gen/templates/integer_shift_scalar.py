#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""One scalar shift amount applied to every element.

The amount is one past the element width, which is the smallest amount the
hardware must reduce modulo the width.
"""

from __future__ import annotations

DOC_ZH = """\
对所有元素施加同一个标量位移量。

位移量比元素宽度大一，这是硬件必须按宽度取模归约的最小位移量。
"""

from mmul_gen.templates.integer_shift_common import IntegerShiftTemplate


class ShiftScalarSource(IntegerShiftTemplate):
    """One scalar shift amount applied to every element."""

    summary_zh = "对所有元素施加同一个标量位移量。"
    name = "shift_scalar_source"

    scalar_amount = True


__all__ = ["ShiftScalarSource"]
