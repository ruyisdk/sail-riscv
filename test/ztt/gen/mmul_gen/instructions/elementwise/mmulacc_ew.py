#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""mmulacc.py: multiply-accumulate of two matrix operands into the destination."""

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
    ElementwiseSaturatingBoundary,
    ElementwiseSaturatingBoundary128,
    FLOAT_OPERATION_VALUES,
    FloatArithmeticRole,
    IntegerElements,
    IntegerInputKind,
    SaturatingExpectation,
    overflow,
)

from mmul_gen.templates.elementwise_emit import (
    CasePlan,
    SOURCE,
    ZERO,
    vector_operands,
)


class MmulaccEw(ElementwiseInstruction):
    """Multiply-accumulate of two matrix operands into the destination."""

    name = "mmulacc.ew"
    summary = "multiply-accumulate of two matrix operands into the destination"
    subject = "elementwise test cases."
    operands = ()
    form = ElementwiseForm.TERNARY_M

    def evaluate(self, elements: IntegerElements) -> int:
        """``D = D + A * B``; the M form shares ``D`` and ``A``."""

        return elements.dest + elements.lhs * elements.rhs

    def evaluate_float(self, dtype_name: str, element_bits: int) -> int:
        """The softfloat model's nominal ``mulacc`` operand is this instruction's answer."""

        return FLOAT_OPERATION_VALUES[dtype_name]["mulacc"]

    #: Every template this instruction runs, in the order its cases appear.
    templates = (
        ElementwiseIntegerValueRules(BASE_INTEGER_INPUT_CASES + (
            overflow(IntegerInputKind.MUL, downward=False),
        ), evaluate),
        ElementwiseIntegerValueRules128(BASE_INTEGER_INPUT_CASES + (
            overflow(IntegerInputKind.MUL, downward=False),
        ), evaluate),
        ElementwiseSaturatingBoundary(
            SaturatingExpectation.MAX,
            CasePlan(vector_operands("max", "one"), ZERO, (SOURCE, SOURCE)),
        ),
        ElementwiseSaturatingBoundary128(
            SaturatingExpectation.MAX,
            CasePlan(vector_operands("max", "one"), ZERO, (SOURCE, SOURCE)),
        ),
        ElementwiseFloatNominal(evaluate_float),
        ElementwiseFloatSpecialValues(FloatArithmeticRole.MULACC),
        ElementwiseFloatSemanticsSweep(FloatArithmeticRole.MULACC),
    )


__all__ = ["MmulaccEw"]
