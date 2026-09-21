#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""mmin.py: minimum of a scalar and a matrix operand."""

from __future__ import annotations

from mmul_gen.instructions.elementwise.base import (
    BASE_INTEGER_INPUT_CASES,
    ElementwiseFloatNominal,
    ElementwiseFloatSpecialValues,
    ElementwiseForm,
    ElementwiseInstruction,
    ElementwiseIntegerValueRules,
    ElementwiseIntegerValueRules128,
    FLOAT_OPERATION_VALUES,
    FloatSpecialRole,
    IntegerElements,
)


class MminEwX(ElementwiseInstruction):
    """Minimum of a scalar and a matrix operand."""

    name = "mmin.ew.x"
    summary = "minimum of a scalar and a matrix operand"
    summary_zh = "标量与矩阵操作数逐元素取最小值"
    subject = "elementwise test cases."
    operands = ()
    form = ElementwiseForm.BINARY_X

    def evaluate(self, elements: IntegerElements) -> int:
        """``D = min(A, B)``. The scalar form reads its scalar as the first operand."""

        return min(elements.lhs, elements.rhs)

    def evaluate_float(self, dtype_name: str, element_bits: int) -> int:
        """The softfloat model's nominal ``b`` operand is this instruction's answer."""

        return FLOAT_OPERATION_VALUES[dtype_name]["b"]

    #: Every template this instruction runs, in the order its cases appear.
    templates = (
        ElementwiseIntegerValueRules(BASE_INTEGER_INPUT_CASES, evaluate),
        ElementwiseIntegerValueRules128(BASE_INTEGER_INPUT_CASES, evaluate),
        ElementwiseFloatNominal(evaluate_float),
        ElementwiseFloatSpecialValues(FloatSpecialRole.MIN),
    )


__all__ = ["MminEwX"]
