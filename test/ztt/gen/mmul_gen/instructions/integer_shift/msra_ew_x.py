#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Generator for ``msra.ew.x``: scalar-form integer shift."""

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


class MsraEwX(Instruction):
    """Arithmetically shift every signed element right by one shared amount."""

    name = "msra.ew.x"
    summary = "arithmetically shift every signed element right by one shared amount"
    summary_zh = "所有带符号元素按同一标量位移量算术右移"
    subject = "integer shift semantic test cases."
    operands = (DESTINATION_OPERAND, SCALAR_SOURCE_OPERAND, FIRST_SOURCE_OPERAND)

    def evaluate(self, value: int, amount: int, element_bits: int) -> int:
        """Shift ``value`` right, replicating its sign bit."""

        mask = (1 << element_bits) - 1
        sign_bit = 1 << (element_bits - 1)
        signed_value = value - (1 << element_bits) if value & sign_bit else value
        return (signed_value >> (amount % element_bits)) & mask

    templates = (ShiftScalarSource(evaluate, signed_only=True),)


__all__ = ["MsraEwX"]
