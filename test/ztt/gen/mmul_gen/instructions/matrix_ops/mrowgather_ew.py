#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Generator for ``mrowgather.ew``: matrix permute/reduce."""

from __future__ import annotations

from mmul_gen.instruction import (
    DESTINATION_OPERAND,
    FIRST_SOURCE_OPERAND,
    SECOND_SOURCE_OPERAND,
)
from mmul_gen.instructions.matrix_ops.base import (
    MatrixAxis,
    MatrixOpsInstruction,
    ScatterAccess,
)
from mmul_gen.templates.matrix_ops_gather_indexed import (
    GatherScatterIndexed,
)

class MrowgatherEw(MatrixOpsInstruction):
    """Gather rows through an element-sized index table."""

    name = "mrowgather.ew"
    summary = "gather rows through an element-sized index table"
    subject = "gather/scatter test cases."
    operands = (DESTINATION_OPERAND, FIRST_SOURCE_OPERAND, SECOND_SOURCE_OPERAND)
    templates = (
        GatherScatterIndexed(MatrixAxis.ROW, ScatterAccess.GATHER),
    )

__all__ = ["MrowgatherEw"]
