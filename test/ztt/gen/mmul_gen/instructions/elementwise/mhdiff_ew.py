#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""mhdiff.py: halving difference of two matrix operands."""

from __future__ import annotations

from mmul_gen.instructions.elementwise.base import (
    BASE_INTEGER_INPUT_CASES,
    ElementwiseForm,
    ElementwiseInstruction,
    ElementwiseIntegerValueRules,
    ElementwiseIntegerValueRules128,
    IntegerElements,
    IntegerInputKind,
    overflow,
    round_to_nearest_up,
)


class MhdiffEw(ElementwiseInstruction):
    """Halving difference of two matrix operands."""

    name = "mhdiff.ew"
    summary = "halving difference of two matrix operands"
    subject = "elementwise test cases."
    operands = ()
    form = ElementwiseForm.BINARY_M

    def evaluate(self, elements: IntegerElements) -> int:
        """``D = (B - A) / 2``, rounded to nearest with ties up."""

        return round_to_nearest_up(elements.rhs - elements.lhs)

    #: Every template this instruction runs, in the order its cases appear.
    templates = (
        ElementwiseIntegerValueRules(BASE_INTEGER_INPUT_CASES + (
            overflow(IntegerInputKind.HDIFF_RTL, downward=False),
        ), evaluate),
        ElementwiseIntegerValueRules128(BASE_INTEGER_INPUT_CASES + (
            overflow(IntegerInputKind.HDIFF_RTL, downward=False),
        ), evaluate),
    )


__all__ = ["MhdiffEw"]
