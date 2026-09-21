#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""mcmovge.py: conditional move when greater-or-equal of two matrix operands into the destination."""

from __future__ import annotations

from mmul_gen.instructions.elementwise.base import (
    BASE_INTEGER_INPUT_CASES,
    ElementwiseForm,
    ElementwiseInstruction,
    ElementwiseIntegerValueRules,
    ElementwiseIntegerValueRules128,
    IntegerElements,
)


class McmovgeEw(ElementwiseInstruction):
    """Conditional move when greater-or-equal of two matrix operands into the destination."""

    name = "mcmovge.ew"
    summary = "conditional move when greater-or-equal of two matrix operands into the destination"
    summary_zh = "两个矩阵操作数比较大于等于成立时，将源条件搬移到目的操作数"
    subject = "elementwise test cases."
    operands = ()
    form = ElementwiseForm.TERNARY_M

    def evaluate(self, elements: IntegerElements) -> int:
        """``D = B`` when ``A >= 0``, else ``D`` keeps its value; the M form shares ``D`` and ``A``."""

        return elements.rhs if elements.lhs >= 0 else elements.dest

    #: Every template this instruction runs, in the order its cases appear.
    templates = (
        ElementwiseIntegerValueRules(BASE_INTEGER_INPUT_CASES, evaluate),
        ElementwiseIntegerValueRules128(BASE_INTEGER_INPUT_CASES, evaluate),
    )


__all__ = ["McmovgeEw"]
