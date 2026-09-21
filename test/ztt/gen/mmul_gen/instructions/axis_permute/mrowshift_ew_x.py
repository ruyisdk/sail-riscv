#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Generator for ``mrowshift.ew.x``: row/column control."""

from __future__ import annotations

from mmul_gen.instruction import (
    DESTINATION_OPERAND,
    FIRST_SOURCE_OPERAND,
    Instruction,
    SCALAR_SOURCE_OPERAND,
)
from mmul_gen.templates.axis_permute_row_shift import (
    ROW_SHIFT,
)


class MrowshiftEwX(Instruction):
    """Shift every column by a signed row amount, zero-filling the edge."""

    name = "mrowshift.ew.x"
    summary = "shift every column by a signed row amount, zero-filling the edge"
    summary_zh = "按带符号的行位移量平移每一列，移出有效方阵的部分补零"
    subject = "row/column semantic test cases."
    operands = (DESTINATION_OPERAND, SCALAR_SOURCE_OPERAND, FIRST_SOURCE_OPERAND)
    templates = (ROW_SHIFT,)


__all__ = ["MrowshiftEwX"]
