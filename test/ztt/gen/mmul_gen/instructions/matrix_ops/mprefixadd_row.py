#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Generator for ``mprefixadd.row``: matrix permute/reduce."""

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
from mmul_gen.templates.matrix_ops_reduce_saturating import (
    REDUCE_SATURATING,
)

class MprefixaddRow(MatrixOpsInstruction):
    """Running sum along each row."""

    name = "mprefixadd.row"
    summary = "running sum along each row"
    summary_zh = "沿每行求前缀和"
    subject = "reduce/prefix test cases."
    operands = (DESTINATION_OPERAND, FIRST_SOURCE_OPERAND)
    templates = (
        ReducePrefixRamp(MatrixAxis.ROW, Reduction.SUM, prefix=True),
        REDUCE_SATURATING,
    )

__all__ = ["MprefixaddRow"]
