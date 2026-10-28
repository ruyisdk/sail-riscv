#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Generator for ``mtanh.ew``: floating-point unary math."""

from __future__ import annotations

from mmul_gen.instruction import (
    DESTINATION_OPERAND,
    FIRST_SOURCE_OPERAND,
)
from mmul_gen.instructions.float_math.base import FloatMathInstruction
from mmul_gen.machine import INTEGER
from mmul_gen.templates.float_math_cases import (
    FloatMathCases,
)
from mmul_gen.templates.float_math_common import MathOperation
from mmul_gen.mixed_math import MixedMathOperation
from mmul_gen.templates.float_mixed_format import FloatMixedFormat
from mmul_gen.templates.logexp_common import LogExpForm
from mmul_gen.templates.logexp_unsupported_source import (
    LogExpUnsupportedSource,
)

class MtanhEw(FloatMathInstruction):
    """Hyperbolic tangent of each element."""

    name = "mtanh.ew"
    summary = "hyperbolic tangent of each element"
    operands = (DESTINATION_OPERAND, FIRST_SOURCE_OPERAND)
    templates = (
        FloatMathCases(MathOperation.TANH),
        FloatMixedFormat(MixedMathOperation.TANH),
        LogExpUnsupportedSource(
            src1_label="mant_square", form=LogExpForm.UNARY, domain=INTEGER
        ),
    )

__all__ = ["MtanhEw"]
