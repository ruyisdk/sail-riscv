#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""mand.py: bitwise and of a scalar and a matrix operand."""

from __future__ import annotations

from mmul_gen.instructions.elementwise.base import (
    BASE_INTEGER_INPUT_CASES,
    ElementwiseForm,
    ElementwiseInstruction,
    ElementwiseIntegerValueRules,
    ElementwiseIntegerValueRules128,
    IntegerElements,
)


class MandEwX(ElementwiseInstruction):
    """Bitwise and of a scalar and a matrix operand."""

    name = "mand.ew.x"
    summary = "bitwise and of a scalar and a matrix operand"
    summary_zh = "标量与矩阵操作数逐元素按位与"
    subject = "elementwise test cases."
    operands = ()
    form = ElementwiseForm.BINARY_X

    def evaluate(self, elements: IntegerElements) -> int:
        """``D = A & B`` on the raw element bits. The scalar form reads its scalar as the first operand."""

        return elements.lhs_raw & elements.rhs_raw

    #: Every template this instruction runs, in the order its cases appear.
    templates = (
        ElementwiseIntegerValueRules(BASE_INTEGER_INPUT_CASES, evaluate),
        ElementwiseIntegerValueRules128(BASE_INTEGER_INPUT_CASES, evaluate),
    )


__all__ = ["MandEwX"]
