#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Generator for ``mcolshift.ew.x``: row/column control."""

from __future__ import annotations

from mmul_gen.instruction import (
    DESTINATION_OPERAND,
    FIRST_SOURCE_OPERAND,
    Instruction,
    SCALAR_SOURCE_OPERAND,
)
from mmul_gen.templates.axis_permute_column_shift import (
    COLUMN_SHIFT,
)


class McolshiftEwX(Instruction):
    """Shift every row by a signed column amount, zero-filling the edge."""

    name = "mcolshift.ew.x"
    summary = "shift every row by a signed column amount, zero-filling the edge"
    summary_zh = "按带符号的列位移量平移每一行，移出有效方阵的部分补零"
    subject = "row/column semantic test cases."
    operands = (DESTINATION_OPERAND, SCALAR_SOURCE_OPERAND, FIRST_SOURCE_OPERAND)
    templates = (COLUMN_SHIFT,)


__all__ = ["McolshiftEwX"]
