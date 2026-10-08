#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Generator for ``mreduceadd.row``: matrix permute/reduce."""

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
from mmul_gen.templates.matrix_ops_saturating_fold import (
    ReducePrefixSaturatingFold,
)

class MreduceaddRow(MatrixOpsInstruction):
    """Sum each row and replicate it across the row."""

    name = "mreduceadd.row"
    summary = "sum each row and replicate it across the row"
    subject = "reduce/prefix test cases."
    operands = (DESTINATION_OPERAND, FIRST_SOURCE_OPERAND)
    templates = (
        ReducePrefixRamp(MatrixAxis.ROW, Reduction.SUM),
        REDUCE_SATURATING,
        ReducePrefixSaturatingFold(MatrixAxis.ROW),
    )

__all__ = ["MreduceaddRow"]
