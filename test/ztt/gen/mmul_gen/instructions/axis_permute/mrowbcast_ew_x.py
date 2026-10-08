#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Generator for ``mrowbcast.ew.x``: row/column control."""

from __future__ import annotations

from mmul_gen.instruction import (
    DESTINATION_OPERAND,
    FIRST_SOURCE_OPERAND,
    Instruction,
    SCALAR_SOURCE_OPERAND,
)
from mmul_gen.templates.axis_permute_row_broadcast import (
    ROW_BROADCAST,
)


class MrowbcastEwX(Instruction):
    """Replicate one source row across every row of each column."""

    name = "mrowbcast.ew.x"
    summary = "replicate one source row across every row of each column"
    subject = "row/column semantic test cases."
    operands = (DESTINATION_OPERAND, SCALAR_SOURCE_OPERAND, FIRST_SOURCE_OPERAND)
    templates = (ROW_BROADCAST,)


__all__ = ["MrowbcastEwX"]
