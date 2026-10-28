#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Generator for ``mls.cm``: memory-order round trip."""

from __future__ import annotations

from mmul_gen.instruction import (
    Instruction,
    M_TRANSFER_OPERAND,
    SCALAR_SOURCE_OPERAND,
)
from mmul_gen.templates.memory_order_col_to_row import (
    MEMORY_ORDER_COL_TO_ROW,
)
from mmul_gen.templates.memory_fault_atomicity import (
    MemoryFaultAtomicity,
    MemoryForm,
)


class MlsCm(Instruction):
    """Load one m register with column-major addressing."""

    name = "mls.cm"
    summary = "load one M register with column-major addressing"
    subject = "row/column-major memory-order test cases."
    operands = (M_TRANSFER_OPERAND, SCALAR_SOURCE_OPERAND)
    templates = (
        MemoryFaultAtomicity(MemoryForm("cm", strided=False, is_load=True)),MEMORY_ORDER_COL_TO_ROW,)


__all__ = ["MlsCm"]
