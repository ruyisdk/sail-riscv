#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""mcmpge.py: compare greater-or-equal of two matrix operands."""

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


class McmpgeEw(ElementwiseInstruction):
    """Compare greater-or-equal of two matrix operands."""

    name = "mcmpge.ew"
    summary = "compare greater-or-equal of two matrix operands"
    summary_zh = "两个矩阵操作数逐元素比较大于等于"
    subject = "elementwise test cases."
    operands = ()
    form = ElementwiseForm.BINARY_M

    def evaluate(self, elements: IntegerElements) -> int:
        """``D`` is all ones when ``A >= B`` and zero otherwise."""

        return elements.mask if elements.lhs >= elements.rhs else 0

    def evaluate_float(self, dtype_name: str, element_bits: int) -> int:
        """``A >= B`` does not hold on the nominal pair, so the answer is zero."""

        return 0

    #: Every template this instruction runs, in the order its cases appear.
    templates = (
        ElementwiseIntegerValueRules(BASE_INTEGER_INPUT_CASES, evaluate),
        ElementwiseIntegerValueRules128(BASE_INTEGER_INPUT_CASES, evaluate),
        ElementwiseFloatNominal(evaluate_float, comparison=True),
        ElementwiseFloatSpecialValues(FloatSpecialRole.COMPARE_TRUE),
    )


__all__ = ["McmpgeEw"]
