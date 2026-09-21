#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Per-element shift amounts read from a second M operand.

The amount square walks the boundary amounts, so consecutive elements pin
down the modulo reduction instead of repeating one sampled amount.
"""

from __future__ import annotations

DOC_ZH = """\
每个元素的位移量从第二个 M 操作数读出。

位移量方阵走过边界位移量，因此相邻元素钉死取模归约，而不是重复同一个抽样位移量。
"""

from mmul_gen.templates.integer_shift_common import IntegerShiftTemplate


class ShiftRegisterSource(IntegerShiftTemplate):
    """Per-element shift amounts read from a second M operand."""

    summary_zh = "每个元素的位移量从第二个 M 操作数读出。"
    name = "shift_register_source"

    scalar_amount = False


__all__ = ["ShiftRegisterSource"]
