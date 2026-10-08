#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Generator for ``mrsqrt.ew``: floating-point unary math."""

from __future__ import annotations

from mmul_gen.instruction import (
    DESTINATION_OPERAND,
    FIRST_SOURCE_OPERAND,
)
from mmul_gen.instructions.float_math.base import FloatMathInstruction
from mmul_gen.templates.float_math_cases import (
    FloatMathCases,
)
from mmul_gen.templates.float_math_common import MathOperation

class MrsqrtEw(FloatMathInstruction):
    """Reciprocal square root of each element."""

    name = "mrsqrt.ew"
    summary = "reciprocal square root of each element"
    operands = (DESTINATION_OPERAND, FIRST_SOURCE_OPERAND)
    templates = (
        FloatMathCases(MathOperation.RECIPROCAL_SQRT),
    )

__all__ = ["MrsqrtEw"]
