#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Generator for ``mss.rm``: memory-order round trip."""

from __future__ import annotations

from mmul_gen.instruction import (
    Instruction,
    M_TRANSFER_OPERAND,
    SCALAR_DESTINATION_OPERAND,
)
from mmul_gen.templates.memory_order_col_to_row import (
    MEMORY_ORDER_COL_TO_ROW,
)


class MssRm(Instruction):
    """Store one m register with row-major addressing."""

    name = "mss.rm"
    summary = "store one M register with row-major addressing"
    summary_zh = "以行主序寻址存储一个 M 寄存器"
    subject = "row/column-major memory-order test cases."
    operands = (M_TRANSFER_OPERAND, SCALAR_DESTINATION_OPERAND)
    templates = (MEMORY_ORDER_COL_TO_ROW,)


__all__ = ["MssRm"]
