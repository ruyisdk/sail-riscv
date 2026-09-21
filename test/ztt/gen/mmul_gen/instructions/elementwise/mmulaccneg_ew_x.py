#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""mmulaccneg.py: negated multiply-accumulate of a scalar and a matrix operand into the destination."""

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


class MmulaccnegEwX(ElementwiseInstruction):
    """Negated multiply-accumulate of a scalar and a matrix operand into the destination."""

    name = "mmulaccneg.ew.x"
    summary = "negated multiply-accumulate of a scalar and a matrix operand into the destination"
    summary_zh = "标量与矩阵操作数逐元素取负乘累加到目的操作数"
    subject = "elementwise test cases."
    operands = ()
    form = ElementwiseForm.TERNARY_X

    def evaluate(self, elements: IntegerElements) -> int:
        """``D = D - A * B``; the M form shares ``D`` and ``A``. The scalar form reads its scalar as the first operand."""

        return elements.dest - elements.lhs * elements.rhs

    def evaluate_float(self, dtype_name: str, element_bits: int) -> int:
        """The softfloat model's nominal ``x_mulaccneg`` operand is this instruction's answer."""

        return FLOAT_OPERATION_VALUES[dtype_name]["x_mulaccneg"]

    #: Every template this instruction runs, in the order its cases appear.
    templates = (
        ElementwiseIntegerValueRules(BASE_INTEGER_INPUT_CASES + (
            overflow(IntegerInputKind.MULNEG, downward=True),
        ), evaluate),
        ElementwiseIntegerValueRules128(BASE_INTEGER_INPUT_CASES + (
            overflow(IntegerInputKind.MULNEG, downward=True),
        ), evaluate),
        ElementwiseFloatNominal(evaluate_float),
        ElementwiseFloatSpecialValues(FloatArithmeticRole.MULACCNEG),
        ElementwiseFloatSemanticsSweep(FloatArithmeticRole.MULACCNEG),
    )


__all__ = ["MmulaccnegEwX"]
