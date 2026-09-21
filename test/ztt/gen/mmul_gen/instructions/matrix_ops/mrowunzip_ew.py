#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Generator for ``mrowunzip.ew``: matrix permute/reduce."""

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

class MrowunzipEw(MatrixOpsInstruction):
    """Split one interleaved row stream into two."""

    name = "mrowunzip.ew"
    summary = "split one interleaved row stream into two"
    summary_zh = "将一路交错的行流拆分为两路"
    subject = "zip/unzip test cases."
    operands = (FIRST_SOURCE_OPERAND, SECOND_SOURCE_OPERAND)
    templates = (
        ZipDualSource(MatrixAxis.ROW, unzip=True),
        ZipExtraSource(MatrixAxis.ROW, unzip=True),
    )

__all__ = ["MrowunzipEw"]
