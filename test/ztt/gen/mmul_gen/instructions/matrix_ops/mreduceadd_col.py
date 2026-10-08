#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Generator for ``mreduceadd.col``: matrix permute/reduce."""

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
from mmul_gen.templates.matrix_ops_saturating_fold import (
    ReducePrefixSaturatingFold,
)

class MreduceaddCol(MatrixOpsInstruction):
    """Sum each column and replicate it down the column."""

    name = "mreduceadd.col"
    summary = "sum each column and replicate it down the column"
    subject = "reduce/prefix test cases."
    operands = (DESTINATION_OPERAND, FIRST_SOURCE_OPERAND)
    templates = (
        ReducePrefixRamp(MatrixAxis.COLUMN, Reduction.SUM),
        ReducePrefixSaturatingFold(MatrixAxis.COLUMN),
    )

__all__ = ["MreduceaddCol"]
