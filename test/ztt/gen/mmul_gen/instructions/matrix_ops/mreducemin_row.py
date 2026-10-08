#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Generator for ``mreducemin.row``: matrix permute/reduce."""

from __future__ import annotations

from mmul_gen.instruction import (
    DESTINATION_OPERAND,
    FIRST_SOURCE_OPERAND,
)
from mmul_gen.instructions.matrix_ops.base import (
    MatrixAxis,
    MatrixOpsInstruction,
    Reduction,
)
from mmul_gen.templates.matrix_ops_reduce_ramp import (
    ReducePrefixRamp,
)

class MreduceminRow(MatrixOpsInstruction):
    """Smallest element of each row, replicated across it."""

    name = "mreducemin.row"
    summary = "smallest element of each row, replicated across it"
    subject = "reduce/prefix test cases."
    operands = (DESTINATION_OPERAND, FIRST_SOURCE_OPERAND)
    templates = (
        ReducePrefixRamp(MatrixAxis.ROW, Reduction.MIN),
    )

__all__ = ["MreduceminRow"]
