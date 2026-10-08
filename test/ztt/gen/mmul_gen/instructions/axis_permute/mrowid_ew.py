#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Generator for ``mrowid.ew``: row/column control."""

from __future__ import annotations

from mmul_gen.instruction import (
    DESTINATION_OPERAND,
    Instruction,
)
from mmul_gen.templates.axis_permute_row_index import (
    ROW_INDEX,
)


class MrowidEw(Instruction):
    """Fill every element with its own row coordinate."""

    name = "mrowid.ew"
    summary = "fill every element with its own row coordinate"
    subject = "row/column semantic test cases."
    operands = (DESTINATION_OPERAND,)
    templates = (ROW_INDEX,)


__all__ = ["MrowidEw"]
