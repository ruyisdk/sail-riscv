#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""mornot.py: bitwise or-not of two matrix operands."""

from __future__ import annotations

from mmul_gen.instructions.elementwise.base import (
    BASE_INTEGER_INPUT_CASES,
    ElementwiseForm,
    ElementwiseInstruction,
    ElementwiseIntegerValueRules,
    ElementwiseIntegerValueRules128,
    IntegerElements,
)


class MornotEw(ElementwiseInstruction):
    """Bitwise or-not of two matrix operands."""

    name = "mornot.ew"
    summary = "bitwise or-not of two matrix operands"
    subject = "elementwise test cases."
    operands = ()
    form = ElementwiseForm.BINARY_M

    def evaluate(self, elements: IntegerElements) -> int:
        """``D = A | ~B`` on the raw element bits."""

        return elements.lhs_raw | ~elements.rhs_raw

    #: Every template this instruction runs, in the order its cases appear.
    templates = (
        ElementwiseIntegerValueRules(BASE_INTEGER_INPUT_CASES, evaluate),
        ElementwiseIntegerValueRules128(BASE_INTEGER_INPUT_CASES, evaluate),
    )


__all__ = ["MornotEw"]
