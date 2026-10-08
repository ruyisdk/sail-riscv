#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Generator for ``msll.ew.x``: scalar-form integer shift."""

from __future__ import annotations

from mmul_gen.instruction import (
    DESTINATION_OPERAND,
    FIRST_SOURCE_OPERAND,
    Instruction,
    SCALAR_SOURCE_OPERAND,
)
from mmul_gen.templates.integer_shift_scalar import (
    ShiftScalarSource,
)


class MsllEwX(Instruction):
    """Shift every element left by one shared scalar amount."""

    name = "msll.ew.x"
    summary = "shift every element left by one shared scalar amount"
    subject = "integer shift semantic test cases."
    operands = (DESTINATION_OPERAND, SCALAR_SOURCE_OPERAND, FIRST_SOURCE_OPERAND)

    def evaluate(self, value: int, amount: int, element_bits: int) -> int:
        """Shift ``value`` left, keeping the element width."""

        mask = (1 << element_bits) - 1
        return (value << (amount % element_bits)) & mask

    templates = (ShiftScalarSource(evaluate),)


__all__ = ["MsllEwX"]
