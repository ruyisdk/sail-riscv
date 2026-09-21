#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Generator for ``mcolbcast.ew.x``: row/column control."""

from __future__ import annotations

from mmul_gen.instruction import (
    DESTINATION_OPERAND,
    FIRST_SOURCE_OPERAND,
    Instruction,
    SCALAR_SOURCE_OPERAND,
)
from mmul_gen.templates.axis_permute_column_broadcast import (
    COLUMN_BROADCAST,
)


class McolbcastEwX(Instruction):
    """Replicate one source column across every column of each row."""

    name = "mcolbcast.ew.x"
    summary = "replicate one source column across every column of each row"
    summary_zh = "将源方阵的某一列复制到每一行的所有列"
    subject = "row/column semantic test cases."
    operands = (DESTINATION_OPERAND, SCALAR_SOURCE_OPERAND, FIRST_SOURCE_OPERAND)
    templates = (COLUMN_BROADCAST,)


__all__ = ["McolbcastEwX"]
