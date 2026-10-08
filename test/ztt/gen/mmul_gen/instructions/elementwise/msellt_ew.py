#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""msellt.py: select on less-than of two matrix operands."""

from __future__ import annotations

from mmul_gen.instructions.elementwise.base import (
    BASE_INTEGER_INPUT_CASES,
    ElementwiseForm,
    ElementwiseInstruction,
    ElementwiseIntegerValueRules,
    ElementwiseIntegerValueRules128,
    IntegerElements,
)


class MselltEw(ElementwiseInstruction):
    """Select on less-than of two matrix operands."""

    name = "msellt.ew"
    summary = "select on less-than of two matrix operands"
    subject = "elementwise test cases."
    operands = ()
    form = ElementwiseForm.BINARY_M

    def evaluate(self, elements: IntegerElements) -> int:
        """``D = B`` when ``A < 0`` and zero otherwise; the compare is numeric."""

        return elements.rhs_raw if elements.lhs < 0 else 0

    #: Every template this instruction runs, in the order its cases appear.
    templates = (
        ElementwiseIntegerValueRules(BASE_INTEGER_INPUT_CASES, evaluate),
        ElementwiseIntegerValueRules128(BASE_INTEGER_INPUT_CASES, evaluate),
    )


__all__ = ["MselltEw"]
