#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""mcmpge.py: compare greater-or-equal of a scalar and a matrix operand."""

from __future__ import annotations

from mmul_gen.instructions.elementwise.base import (
    BASE_INTEGER_INPUT_CASES,
    ElementwiseFloatNominal,
    ElementwiseFloatSpecialValues,
    ElementwiseForm,
    ElementwiseInstruction,
    ElementwiseIntegerValueRules,
    ElementwiseIntegerValueRules128,
    FloatSpecialRole,
    IntegerElements,
)


class McmpgeEwX(ElementwiseInstruction):
    """Compare greater-or-equal of a scalar and a matrix operand."""

    name = "mcmpge.ew.x"
    summary = "compare greater-or-equal of a scalar and a matrix operand"
    summary_zh = "标量与矩阵操作数逐元素比较大于等于"
    subject = "elementwise test cases."
    operands = ()
    form = ElementwiseForm.BINARY_X

    def evaluate(self, elements: IntegerElements) -> int:
        """``D`` is all ones when ``A >= B`` and zero otherwise. The scalar form reads its scalar as the first operand."""

        return elements.mask if elements.lhs >= elements.rhs else 0

    def evaluate_float(self, dtype_name: str, element_bits: int) -> int:
        """``scalar >= B`` holds on the nominal pair, so the answer is the all-ones mask."""

        return (1 << element_bits) - 1

    #: Every template this instruction runs, in the order its cases appear.
    templates = (
        ElementwiseIntegerValueRules(BASE_INTEGER_INPUT_CASES, evaluate),
        ElementwiseIntegerValueRules128(BASE_INTEGER_INPUT_CASES, evaluate),
        ElementwiseFloatNominal(evaluate_float, comparison=True),
        ElementwiseFloatSpecialValues(FloatSpecialRole.COMPARE_TRUE),
    )


__all__ = ["McmpgeEwX"]
