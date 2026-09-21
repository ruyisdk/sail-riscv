#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""mmov.py: move between matrix operands."""

from __future__ import annotations

from mmul_gen.instructions.elementwise.base import (
    BASE_INTEGER_INPUT_CASES,
    ElementwiseForm,
    ElementwiseInstruction,
    ElementwiseIntegerValueRules,
    ElementwiseIntegerValueRules128,
    IntegerElements,
)


class MmovMM(ElementwiseInstruction):
    """Move between matrix operands."""

    name = "mmov.m.m"
    summary = "move between matrix operands"
    summary_zh = "在矩阵操作数之间搬移"
    subject = "elementwise test cases."
    operands = ()
    form = ElementwiseForm.MOVE_M

    def evaluate(self, elements: IntegerElements) -> int:
        """``D = B``: a move copies the source square."""

        return elements.rhs

    #: Every template this instruction runs, in the order its cases appear.
    templates = (
        ElementwiseIntegerValueRules(BASE_INTEGER_INPUT_CASES, evaluate),
        ElementwiseIntegerValueRules128(BASE_INTEGER_INPUT_CASES, evaluate),
    )


__all__ = ["MmovMM"]
