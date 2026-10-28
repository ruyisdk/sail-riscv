#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Generator for ``mexp2.ew``: integer log/exp."""

from __future__ import annotations

from mmul_gen.instruction import (
    DESTINATION_OPERAND,
    FIRST_SOURCE_OPERAND,
)
from mmul_gen.instructions.logexp.base import (
    LogExpForm,
    LogExpInstruction,
)
from mmul_gen.machine import INTEGER, SATURATING_INTEGER, SATURATING_INTEGER128
from mmul_gen.mixed_math import MixedMathOperation
from mmul_gen.templates.float_mixed_format import FloatMixedFormat
from mmul_gen.templates.logexp_unsupported_source import (
    LogExpUnsupportedSource,
)

class Mexp2Ew(LogExpInstruction):
    """Raise two to each element's exponent."""

    name = "mexp2.ew"
    summary = "raise two to each element's exponent"
    subject = "integer log/exp test cases."
    operands = (DESTINATION_OPERAND, FIRST_SOURCE_OPERAND)
    # v0.6 §6.2.2 requires a floating-point source and destination for mexp2.ew,
    # so every standard integer domain below is an unsupported tuple.  The three
    # domains are the ones the instruction used to cover with integer semantics,
    # kept so the rejection is probed at the plain, saturating, and 128-bit
    # descriptor widths.
    templates = (
        # v0.6 §6.2.2 makes the source and the destination floating point but
        # never asks them to share a format, so a mixed tuple runs.
        FloatMixedFormat(MixedMathOperation.EXP2),
        LogExpUnsupportedSource(
            src1_label="exp_square", form=LogExpForm.UNARY, domain=INTEGER
        ),
        LogExpUnsupportedSource(
            src1_label="exp_square", form=LogExpForm.UNARY, domain=SATURATING_INTEGER
        ),
        LogExpUnsupportedSource(
            src1_label="exp_square", form=LogExpForm.UNARY, domain=SATURATING_INTEGER128
        ),
    )

__all__ = ["Mexp2Ew"]
