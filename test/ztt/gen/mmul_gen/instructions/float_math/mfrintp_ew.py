#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Generator for ``mfrintp.ew``: floating-point unary math."""

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
from mmul_gen.templates.float_ignored_rm import FloatIgnoredRoundingMode
from mmul_gen.templates.float_mixed_format import FloatMixedFormat
from mmul_gen.templates.float_rounding_overflow import FloatRoundingOverflow
from mmul_gen.templates.logexp_common import LogExpForm
from mmul_gen.templates.logexp_unsupported_source import (
    LogExpUnsupportedSource,
)

class MfrintpEw(FloatMathInstruction):
    """Round each element toward plus infinity."""

    name = "mfrintp.ew"
    summary = "round each element toward plus infinity"
    operands = (DESTINATION_OPERAND, FIRST_SOURCE_OPERAND)
    templates = (
        FloatMathCases(MathOperation.CEIL),
        FloatMixedFormat(MixedMathOperation.CEIL),
        FloatIgnoredRoundingMode(MixedMathOperation.CEIL),
        FloatRoundingOverflow(MixedMathOperation.CEIL),
        LogExpUnsupportedSource(
            src1_label="mant_square", form=LogExpForm.UNARY, domain=INTEGER
        ),
    )

__all__ = ["MfrintpEw"]
