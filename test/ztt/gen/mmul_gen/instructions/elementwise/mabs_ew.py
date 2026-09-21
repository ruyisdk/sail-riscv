#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""mabs.py: absolute value of a matrix operand."""

from __future__ import annotations

from mmul_gen.instructions.elementwise.base import (
    BASE_INTEGER_INPUT_CASES,
    ElementwiseFloatNominal,
    ElementwiseFloatSpecialValues,
    ElementwiseForm,
    ElementwiseInstruction,
    ElementwiseIntegerValueRules,
    ElementwiseIntegerValueRules128,
    ElementwiseSaturatingBoundary,
    ElementwiseSaturatingBoundary128,
    FLOAT_OPERATION_VALUES,
    FloatSpecialRole,
    IntegerElements,
    SaturatingExpectation,
)

from mmul_gen.templates.elementwise_emit import (
    CasePlan,
    Operand,
    ZERO,
)


class MabsEw(ElementwiseInstruction):
    """Absolute value of a matrix operand."""

    name = "mabs.ew"
    summary = "absolute value of a matrix operand"
    summary_zh = "对矩阵操作数逐元素取绝对值"
    subject = "elementwise test cases."
    operands = ()
    form = ElementwiseForm.UNARY_ABS

    def evaluate(self, elements: IntegerElements) -> int:
        """``D = |A|``."""

        return abs(elements.lhs)

    def evaluate_float(self, dtype_name: str, element_bits: int) -> int:
        """The softfloat model's nominal ``a`` operand is this instruction's answer."""

        return FLOAT_OPERATION_VALUES[dtype_name]["a"]

    #: Every template this instruction runs, in the order its cases appear.
    templates = (
        ElementwiseIntegerValueRules(BASE_INTEGER_INPUT_CASES, evaluate),
        ElementwiseIntegerValueRules128(BASE_INTEGER_INPUT_CASES, evaluate),
        ElementwiseSaturatingBoundary(
            SaturatingExpectation.MAX,
            CasePlan((Operand("abs", "t1", ZERO),), ZERO, (ZERO,)),
        ),
        ElementwiseSaturatingBoundary128(
            SaturatingExpectation.MAX,
            CasePlan((Operand("abs", "t1", ZERO),), ZERO, (ZERO,)),
        ),
        ElementwiseFloatNominal(evaluate_float),
        ElementwiseFloatSpecialValues(FloatSpecialRole.ABS),
    )


__all__ = ["MabsEw"]
