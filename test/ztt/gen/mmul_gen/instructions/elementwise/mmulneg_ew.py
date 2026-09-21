#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""mmulneg.py: negated multiply of two matrix operands."""

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


class MmulnegEw(ElementwiseInstruction):
    """Negated multiply of two matrix operands."""

    name = "mmulneg.ew"
    summary = "negated multiply of two matrix operands"
    summary_zh = "两个矩阵操作数逐元素取负相乘"
    subject = "elementwise test cases."
    operands = ()
    form = ElementwiseForm.BINARY_M

    def evaluate(self, elements: IntegerElements) -> int:
        """``D = -(A * B)``."""

        return -(elements.lhs * elements.rhs)

    def evaluate_float(self, dtype_name: str, element_bits: int) -> int:
        """The softfloat model's nominal ``mulneg`` operand is this instruction's answer."""

        return FLOAT_OPERATION_VALUES[dtype_name]["mulneg"]

    #: Every template this instruction runs, in the order its cases appear.
    templates = (
        ElementwiseIntegerValueRules(BASE_INTEGER_INPUT_CASES + (
            overflow(IntegerInputKind.MULNEG, downward=True),
        ), evaluate),
        ElementwiseIntegerValueRules128(BASE_INTEGER_INPUT_CASES + (
            overflow(IntegerInputKind.MULNEG, downward=True),
        ), evaluate),
        ElementwiseFloatNominal(evaluate_float),
        ElementwiseFloatSpecialValues(FloatArithmeticRole.MULNEG),
        ElementwiseFloatSemanticsSweep(FloatArithmeticRole.MULNEG),
    )


__all__ = ["MmulnegEw"]
