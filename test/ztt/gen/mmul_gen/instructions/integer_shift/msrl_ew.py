#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Generator for ``msrl.ew``: M-operand-form integer shift."""

from __future__ import annotations

from mmul_gen.instruction import (
    DESTINATION_OPERAND,
    FIRST_SOURCE_OPERAND,
    Instruction,
    SECOND_SOURCE_OPERAND,
)
from mmul_gen.templates.integer_shift_register import (
    ShiftRegisterSource,
)


class MsrlEw(Instruction):
    """Logically shift every element right by its own modulo-reduced amount."""

    name = "msrl.ew"
    summary = "logically shift every element right by its own modulo-reduced amount"
    summary_zh = "每个元素按各自的取模归约位移量逻辑右移"
    subject = "integer shift semantic test cases."
    operands = (DESTINATION_OPERAND, FIRST_SOURCE_OPERAND, SECOND_SOURCE_OPERAND)

    def evaluate(self, value: int, amount: int, element_bits: int) -> int:
        """Shift ``value`` right, filling with zeros."""

        return value >> (amount % element_bits)

    templates = (ShiftRegisterSource(evaluate),)


__all__ = ["MsrlEw"]
