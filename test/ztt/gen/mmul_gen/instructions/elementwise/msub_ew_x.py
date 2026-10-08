#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""msub.py: subtract of a scalar and a matrix operand."""

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
    Operand,
    SCALAR,
    SCALAR_DEST,
    ZERO,
)


class MsubEwX(ElementwiseInstruction):
    """Subtract of a scalar and a matrix operand."""

    name = "msub.ew.x"
    summary = "subtract of a scalar and a matrix operand"
    subject = "elementwise test cases."
    operands = ()
    form = ElementwiseForm.BINARY_X

    def evaluate(self, elements: IntegerElements) -> int:
        """``D = B - A``: both forms subtract the first operand from the second. The scalar form reads its scalar as the first operand."""

        return elements.rhs - elements.lhs

    def evaluate_float(self, dtype_name: str, element_bits: int) -> int:
        """The softfloat model's nominal ``x_sub`` operand is this instruction's answer."""

        return FLOAT_OPERATION_VALUES[dtype_name]["x_sub"]

    #: Every template this instruction runs, in the order its cases appear.
    templates = (
        ElementwiseIntegerValueRules(BASE_INTEGER_INPUT_CASES + (
            overflow(IntegerInputKind.SUB_LTR, downward=True),
        ), evaluate),
        ElementwiseIntegerValueRules128(BASE_INTEGER_INPUT_CASES + (
            overflow(IntegerInputKind.SUB_LTR, downward=True),
        ), evaluate),
        # The scalar is materialised rather than loaded from a square, and the
        # dtype floor minus one is what underflows.
        ElementwiseSaturatingBoundary(
            SaturatingExpectation.MIN,
            CasePlan((Operand("one", "t4"), Operand("underflow_rhs", "t2", ZERO)), SCALAR_DEST, (SCALAR, ZERO)),
        ),
        ElementwiseSaturatingBoundary128(
            SaturatingExpectation.MIN,
            CasePlan((Operand("one", "t4"), Operand("underflow_rhs", "t2", ZERO)), SCALAR_DEST, (SCALAR, ZERO)),
        ),
        ElementwiseFloatNominal(evaluate_float),
        ElementwiseFloatSpecialValues(FloatArithmeticRole.SUB),
        ElementwiseFloatSemanticsSweep(FloatArithmeticRole.SUB),
    )


__all__ = ["MsubEwX"]
