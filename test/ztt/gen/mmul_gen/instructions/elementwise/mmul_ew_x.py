#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""mmul.py: multiply of a scalar and a matrix operand."""

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
    FLOAT_OPERATION_VALUES,
    FloatArithmeticRole,
    IntegerElements,
    IntegerInputKind,
    overflow,
)


class MmulEwX(ElementwiseInstruction):
    """Multiply of a scalar and a matrix operand."""

    name = "mmul.ew.x"
    summary = "multiply of a scalar and a matrix operand"
    subject = "elementwise test cases."
    operands = ()
    form = ElementwiseForm.BINARY_X

    def evaluate(self, elements: IntegerElements) -> int:
        """``D = A * B``. The scalar form reads its scalar as the first operand."""

        return elements.lhs * elements.rhs

    def evaluate_float(self, dtype_name: str, element_bits: int) -> int:
        """The softfloat model's nominal ``x_mul`` operand is this instruction's answer."""

        return FLOAT_OPERATION_VALUES[dtype_name]["x_mul"]

    #: Every template this instruction runs, in the order its cases appear.
    templates = (
        ElementwiseIntegerValueRules(BASE_INTEGER_INPUT_CASES + (
            overflow(IntegerInputKind.MUL, downward=False),
        ), evaluate),
        ElementwiseIntegerValueRules128(BASE_INTEGER_INPUT_CASES + (
            overflow(IntegerInputKind.MUL, downward=False),
        ), evaluate),
        ElementwiseFloatNominal(evaluate_float),
        ElementwiseFloatSpecialValues(FloatArithmeticRole.MUL),
        ElementwiseFloatSemanticsSweep(FloatArithmeticRole.MUL),
    )


__all__ = ["MmulEwX"]
