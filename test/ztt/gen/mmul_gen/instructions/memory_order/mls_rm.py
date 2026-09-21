#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Generator for ``mls.rm``: memory-order round trip."""

from __future__ import annotations

from mmul_gen.instruction import (
    Instruction,
    M_TRANSFER_OPERAND,
    SCALAR_SOURCE_OPERAND,
)
from mmul_gen.templates.memory_order_row_to_col import (
    MEMORY_ORDER_ROW_TO_COL,
)


class MlsRm(Instruction):
    """Load one m register with row-major addressing."""

    name = "mls.rm"
    summary = "load one M register with row-major addressing"
    summary_zh = "以行主序寻址加载一个 M 寄存器"
    subject = "row/column-major memory-order test cases."
    operands = (M_TRANSFER_OPERAND, SCALAR_SOURCE_OPERAND)
    templates = (MEMORY_ORDER_ROW_TO_COL,)


__all__ = ["MlsRm"]
