#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Generator for ``mss.cm``: memory-order round trip."""

from __future__ import annotations

from mmul_gen.instruction import (
    Instruction,
    M_TRANSFER_OPERAND,
    SCALAR_DESTINATION_OPERAND,
)
from mmul_gen.templates.memory_order_row_to_col import (
    MEMORY_ORDER_ROW_TO_COL,
)


class MssCm(Instruction):
    """Store one m register with column-major addressing."""

    name = "mss.cm"
    summary = "store one M register with column-major addressing"
    summary_zh = "以列主序寻址存储一个 M 寄存器"
    subject = "row/column-major memory-order test cases."
    operands = (M_TRANSFER_OPERAND, SCALAR_DESTINATION_OPERAND)
    templates = (MEMORY_ORDER_ROW_TO_COL,)


__all__ = ["MssCm"]
