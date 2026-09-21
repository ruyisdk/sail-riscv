#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Generator for ``mprefixmax.col``: matrix permute/reduce."""

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

class MprefixmaxCol(MatrixOpsInstruction):
    """Running maximum down each column."""

    name = "mprefixmax.col"
    summary = "running maximum down each column"
    summary_zh = "沿每列向下求前缀最大值"
    subject = "reduce/prefix test cases."
    operands = (DESTINATION_OPERAND, FIRST_SOURCE_OPERAND)
    templates = (
        ReducePrefixRamp(MatrixAxis.COLUMN, Reduction.MAX, prefix=True),
    )

__all__ = ["MprefixmaxCol"]
