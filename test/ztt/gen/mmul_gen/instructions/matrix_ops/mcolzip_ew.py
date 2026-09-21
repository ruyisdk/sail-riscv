#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Generator for ``mcolzip.ew``: matrix permute/reduce."""

from __future__ import annotations

from mmul_gen.instruction import (
    FIRST_SOURCE_OPERAND,
    SECOND_SOURCE_OPERAND,
)
from mmul_gen.instructions.matrix_ops.base import (
    MatrixAxis,
    MatrixOpsInstruction,
)
from mmul_gen.templates.matrix_ops_zip_dual import (
    ZipDualSource,
)
from mmul_gen.templates.matrix_ops_zip_extra import (
    ZipExtraSource,
)

class McolzipEw(MatrixOpsInstruction):
    """Interleave two source squares into one column stream."""

    name = "mcolzip.ew"
    summary = "interleave two source squares into one column stream"
    summary_zh = "将两个源方阵交错合并为一路列流"
    subject = "zip/unzip test cases."
    operands = (FIRST_SOURCE_OPERAND, SECOND_SOURCE_OPERAND)
    templates = (
        ZipDualSource(MatrixAxis.COLUMN),
        ZipExtraSource(MatrixAxis.COLUMN),
    )

__all__ = ["McolzipEw"]
