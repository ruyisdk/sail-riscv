#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""mmulsub.py: fused multiply-subtract of a scalar and a matrix operand into the destination."""

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


class MmulsubEwX(ElementwiseInstruction):
    """Fused multiply-subtract of a scalar and a matrix operand into the destination."""

    name = "mmulsub.ew.x"
    summary = "fused multiply-subtract of a scalar and a matrix operand into the destination"
    summary_zh = "标量与矩阵操作数逐元素融合乘减到目的操作数"
    subject = "elementwise test cases."
    operands = ()
    form = ElementwiseForm.TERNARY_X

    def evaluate(self, elements: IntegerElements) -> int:
        """``D = A - B * D``; the M form shares ``D`` and ``A``. The scalar form reads its scalar as the first operand."""

        return elements.lhs - elements.rhs * elements.dest

    def evaluate_float(self, dtype_name: str, element_bits: int) -> int:
        """The softfloat model's nominal ``x_mulsub`` operand is this instruction's answer."""

        return FLOAT_OPERATION_VALUES[dtype_name]["x_mulsub"]

    #: Every template this instruction runs, in the order its cases appear.
    templates = (
        ElementwiseIntegerValueRules(BASE_INTEGER_INPUT_CASES + (
            overflow(IntegerInputKind.MUL, downward=True),
        ), evaluate),
        ElementwiseIntegerValueRules128(BASE_INTEGER_INPUT_CASES + (
            overflow(IntegerInputKind.MUL, downward=True),
        ), evaluate),
        ElementwiseFloatNominal(evaluate_float),
        ElementwiseFloatSpecialValues(FloatArithmeticRole.MULSUB),
        ElementwiseFloatSemanticsSweep(FloatArithmeticRole.MULSUB),
    )


__all__ = ["MmulsubEwX"]
