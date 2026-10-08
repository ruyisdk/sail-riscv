#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""mmax.py: maximum of two matrix operands."""

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


class MmaxEw(ElementwiseInstruction):
    """Maximum of two matrix operands."""

    name = "mmax.ew"
    summary = "maximum of two matrix operands"
    subject = "elementwise test cases."
    operands = ()
    form = ElementwiseForm.BINARY_M

    def evaluate(self, elements: IntegerElements) -> int:
        """``D = max(A, B)``."""

        return max(elements.lhs, elements.rhs)

    def evaluate_float(self, dtype_name: str, element_bits: int) -> int:
        """The softfloat model's nominal ``b`` operand is this instruction's answer."""

        return FLOAT_OPERATION_VALUES[dtype_name]["b"]

    #: Every template this instruction runs, in the order its cases appear.
    templates = (
        ElementwiseIntegerValueRules(BASE_INTEGER_INPUT_CASES, evaluate),
        ElementwiseIntegerValueRules128(BASE_INTEGER_INPUT_CASES, evaluate),
        ElementwiseFloatNominal(evaluate_float),
        ElementwiseFloatSpecialValues(FloatSpecialRole.MAX),
    )


__all__ = ["MmaxEw"]
