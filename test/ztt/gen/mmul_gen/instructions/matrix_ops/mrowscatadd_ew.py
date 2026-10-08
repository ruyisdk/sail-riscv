#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Generator for ``mrowscatadd.ew``: matrix permute/reduce."""

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
from mmul_gen.templates.matrix_ops_scatter_saturating import (
    SCATTER_SATURATING,
)

class MrowscataddEw(MatrixOpsInstruction):
    """Scatter-add rows through an index table."""

    name = "mrowscatadd.ew"
    summary = "scatter-add rows through an index table"
    subject = "gather/scatter test cases."
    operands = (DESTINATION_OPERAND, FIRST_SOURCE_OPERAND, SECOND_SOURCE_OPERAND)
    templates = (
        GatherScatterIndexed(MatrixAxis.ROW, access=ScatterAccess.ADD),
        SCATTER_SATURATING,
    )

__all__ = ["MrowscataddEw"]
