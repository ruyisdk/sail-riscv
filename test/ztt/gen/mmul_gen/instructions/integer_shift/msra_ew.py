#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Generator for ``msra.ew``: M-operand-form integer shift."""

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


class MsraEw(Instruction):
    """Arithmetically shift every signed element right by its own amount."""

    name = "msra.ew"
    summary = "arithmetically shift every signed element right by its own amount"
    subject = "integer shift semantic test cases."
    operands = (DESTINATION_OPERAND, FIRST_SOURCE_OPERAND, SECOND_SOURCE_OPERAND)

    def evaluate(self, value: int, amount: int, element_bits: int) -> int:
        """Shift ``value`` right, replicating its sign bit."""

        mask = (1 << element_bits) - 1
        sign_bit = 1 << (element_bits - 1)
        signed_value = value - (1 << element_bits) if value & sign_bit else value
        return (signed_value >> (amount % element_bits)) & mask

    templates = (ShiftRegisterSource(evaluate, signed_only=True),)


__all__ = ["MsraEw"]
