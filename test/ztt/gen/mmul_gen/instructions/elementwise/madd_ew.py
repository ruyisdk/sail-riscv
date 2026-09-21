#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""madd.py: add of two matrix operands."""

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


class MaddEw(ElementwiseInstruction):
    """Add of two matrix operands."""

    name = "madd.ew"
    summary = "add of two matrix operands"
    summary_zh = "两个矩阵操作数逐元素相加"
    subject = "elementwise test cases."
    operands = ()
    form = ElementwiseForm.BINARY_M

    def evaluate(self, elements: IntegerElements) -> int:
        """``D = A + B`` element by element."""

        return elements.lhs + elements.rhs

    def evaluate_float(self, dtype_name: str, element_bits: int) -> int:
        """The softfloat model's nominal ``add`` operand is this instruction's answer."""

        return FLOAT_OPERATION_VALUES[dtype_name]["add"]

    #: Every template this instruction runs, in the order its cases appear.
    templates = (
        ElementwiseIntegerValueRules(BASE_INTEGER_INPUT_CASES + (
            overflow(IntegerInputKind.ADD, downward=False),
        ), evaluate),
        ElementwiseIntegerValueRules128(BASE_INTEGER_INPUT_CASES + (
            overflow(IntegerInputKind.ADD, downward=False),
        ), evaluate),
        ElementwiseSaturatingBoundary(
            SaturatingExpectation.MAX,
            CasePlan(vector_operands("max", "one"), ZERO, (ZERO, SOURCE)),
        ),
        ElementwiseSaturatingBoundary128(
            SaturatingExpectation.MAX,
            CasePlan(vector_operands("max", "one"), ZERO, (ZERO, SOURCE)),
        ),
        ElementwiseFloatNominal(evaluate_float),
        ElementwiseFloatSpecialValues(FloatArithmeticRole.ADD),
        ElementwiseFloatSemanticsSweep(FloatArithmeticRole.ADD),
    )


__all__ = ["MaddEw"]
