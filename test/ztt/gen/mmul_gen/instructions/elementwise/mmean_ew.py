#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""mmean.py: mean of two matrix operands."""

from __future__ import annotations

from mmul_gen.instructions.elementwise.base import (
    BASE_INTEGER_INPUT_CASES,
    ElementwiseForm,
    ElementwiseInstruction,
    ElementwiseIntegerValueRules,
    ElementwiseIntegerValueRules128,
    IntegerElements,
    round_to_nearest_up,
)


class MmeanEw(ElementwiseInstruction):
    """Mean of two matrix operands."""

    name = "mmean.ew"
    summary = "mean of two matrix operands"
    subject = "elementwise test cases."
    operands = ()
    form = ElementwiseForm.BINARY_M

    def evaluate(self, elements: IntegerElements) -> int:
        """``D = (A + B) / 2``, rounded to nearest with ties up."""

        return round_to_nearest_up(elements.lhs + elements.rhs)

    #: Every template this instruction runs, in the order its cases appear.
    templates = (
        ElementwiseIntegerValueRules(BASE_INTEGER_INPUT_CASES, evaluate),
        ElementwiseIntegerValueRules128(BASE_INTEGER_INPUT_CASES, evaluate),
    )


__all__ = ["MmeanEw"]
