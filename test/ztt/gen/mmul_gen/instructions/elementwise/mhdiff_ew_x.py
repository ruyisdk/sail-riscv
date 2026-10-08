#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""mhdiff.py: halving difference of a scalar and a matrix operand."""

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


class MhdiffEwX(ElementwiseInstruction):
    """Halving difference of a scalar and a matrix operand."""

    name = "mhdiff.ew.x"
    summary = "halving difference of a scalar and a matrix operand"
    subject = "elementwise test cases."
    operands = ()
    form = ElementwiseForm.BINARY_X

    def evaluate(self, elements: IntegerElements) -> int:
        """``D = (B - A) / 2``, rounded to nearest with ties up. The scalar form reads its scalar as the first operand."""

        return round_to_nearest_up(elements.rhs - elements.lhs)

    #: Every template this instruction runs, in the order its cases appear.
    templates = (
        ElementwiseIntegerValueRules(BASE_INTEGER_INPUT_CASES + (
            overflow(IntegerInputKind.HDIFF_LTR, downward=False),
        ), evaluate),
        ElementwiseIntegerValueRules128(BASE_INTEGER_INPUT_CASES + (
            overflow(IntegerInputKind.HDIFF_LTR, downward=False),
        ), evaluate),
    )


__all__ = ["MhdiffEwX"]
