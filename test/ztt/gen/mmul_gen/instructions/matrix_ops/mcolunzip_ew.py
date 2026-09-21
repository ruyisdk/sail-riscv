#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Generator for ``mcolunzip.ew``: matrix permute/reduce."""

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

class McolunzipEw(MatrixOpsInstruction):
    """Split one interleaved column stream into two."""

    name = "mcolunzip.ew"
    summary = "split one interleaved column stream into two"
    summary_zh = "将一路交错的列流拆分为两路"
    subject = "zip/unzip test cases."
    operands = (FIRST_SOURCE_OPERAND, SECOND_SOURCE_OPERAND)
    templates = (
        ZipDualSource(MatrixAxis.COLUMN, unzip=True),
        ZipExtraSource(MatrixAxis.COLUMN, unzip=True),
    )

__all__ = ["McolunzipEw"]
