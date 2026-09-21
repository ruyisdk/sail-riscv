#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Generator for ``msrl.ew.x``: scalar-form integer shift."""

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


class MsrlEwX(Instruction):
    """Logically shift every element right by one shared scalar amount."""

    name = "msrl.ew.x"
    summary = "logically shift every element right by one shared scalar amount"
    summary_zh = "所有元素按同一标量位移量逻辑右移"
    subject = "integer shift semantic test cases."
    operands = (DESTINATION_OPERAND, SCALAR_SOURCE_OPERAND, FIRST_SOURCE_OPERAND)

    def evaluate(self, value: int, amount: int, element_bits: int) -> int:
        """Shift ``value`` right, filling with zeros."""

        return value >> (amount % element_bits)

    templates = (ShiftScalarSource(evaluate),)


__all__ = ["MsrlEwX"]
