#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Generator for ``mcolid.ew``: row/column control."""

from __future__ import annotations

from mmul_gen.instruction import (
    DESTINATION_OPERAND,
    Instruction,
)
from mmul_gen.templates.axis_permute_column_index import (
    COLUMN_INDEX,
)


class McolidEw(Instruction):
    """Fill every element with its own column coordinate."""

    name = "mcolid.ew"
    summary = "fill every element with its own column coordinate"
    subject = "row/column semantic test cases."
    operands = (DESTINATION_OPERAND,)
    templates = (COLUMN_INDEX,)


__all__ = ["McolidEw"]
