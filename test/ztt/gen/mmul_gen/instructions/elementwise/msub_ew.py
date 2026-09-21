#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""msub.py: subtract of two matrix operands."""

from __future__ import annotations

from mmul_gen.instructions.elementwise.base import (
    BASE_INTEGER_INPUT_CASES,
    ElementwiseFloatNominal,
    ElementwiseFloatSemanticsSweep,
    ElementwiseFloatSpecialValues,
    ElementwiseForm,
    ElementwiseInstruction,
    ElementwiseIntegerValueRules,
    ElementwiseIntegerValueRules128,
    ElementwiseSaturatingBoundary,
    ElementwiseSaturatingBoundary128,
    FLOAT_OPERATION_VALUES,
    FloatArithmeticRole,
    IntegerElements,
    IntegerInputKind,
    SaturatingExpectation,
    overflow,
)

from mmul_gen.templates.elementwise_emit import (
    CasePlan,
    SOURCE,
    ZERO,
    vector_operands,
)


class MsubEw(ElementwiseInstruction):
    """Subtract of two matrix operands."""

    name = "msub.ew"
    summary = "subtract of two matrix operands"
    summary_zh = "两个矩阵操作数逐元素相减"
    subject = "elementwise test cases."
    operands = ()
    form = ElementwiseForm.BINARY_M

    def evaluate(self, elements: IntegerElements) -> int:
        """``D = B - A``: both forms subtract the first operand from the second."""

        return elements.rhs - elements.lhs

    def evaluate_float(self, dtype_name: str, element_bits: int) -> int:
        """The softfloat model's nominal ``sub`` operand is this instruction's answer."""

        return FLOAT_OPERATION_VALUES[dtype_name]["sub"]

    #: Every template this instruction runs, in the order its cases appear.
    templates = (
        ElementwiseIntegerValueRules(BASE_INTEGER_INPUT_CASES + (
            overflow(IntegerInputKind.SUB_RTL, downward=True),
        ), evaluate),
        ElementwiseIntegerValueRules128(BASE_INTEGER_INPUT_CASES + (
            overflow(IntegerInputKind.SUB_RTL, downward=True),
        ), evaluate),
        ElementwiseSaturatingBoundary(
            SaturatingExpectation.MIN,
            CasePlan(vector_operands("underflow_lhs", "underflow_rhs"), ZERO, (ZERO, SOURCE)),
        ),
        ElementwiseSaturatingBoundary128(
            SaturatingExpectation.MIN,
            CasePlan(vector_operands("underflow_lhs", "underflow_rhs"), ZERO, (ZERO, SOURCE)),
        ),
        ElementwiseFloatNominal(evaluate_float),
        ElementwiseFloatSpecialValues(FloatArithmeticRole.SUB),
        ElementwiseFloatSemanticsSweep(FloatArithmeticRole.SUB),
    )


__all__ = ["MsubEw"]
