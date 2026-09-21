#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Generator for ``mcolscatmax.ew``: matrix permute/reduce."""

from __future__ import annotations

from mmul_gen.instruction import (
    DESTINATION_OPERAND,
    FIRST_SOURCE_OPERAND,
    SECOND_SOURCE_OPERAND,
)
from mmul_gen.instructions.matrix_ops.base import (
    MatrixOpsInstruction,
    MatrixAxis,
    ScatterAccess,
)
from mmul_gen.templates.matrix_ops_gather_indexed import (
    GatherScatterIndexed,
)

class McolscatmaxEw(MatrixOpsInstruction):
    """Scatter-max columns through an index table."""

    name = "mcolscatmax.ew"
    summary = "scatter-max columns through an index table"
    summary_zh = "通过索引表按列散射取最大值"
    subject = "gather/scatter test cases."
    operands = (DESTINATION_OPERAND, FIRST_SOURCE_OPERAND, SECOND_SOURCE_OPERAND)
    templates = (
        GatherScatterIndexed(MatrixAxis.COLUMN, access=ScatterAccess.MAX),
    )

__all__ = ["McolscatmaxEw"]
