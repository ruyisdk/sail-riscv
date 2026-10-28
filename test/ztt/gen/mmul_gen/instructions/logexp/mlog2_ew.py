#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Generator for ``mlog2.ew``: integer log/exp."""

from __future__ import annotations

from mmul_gen.instruction import (
    DESTINATION_OPERAND,
    FIRST_SOURCE_OPERAND,
)
from mmul_gen.instructions.logexp.base import (
    LogExpForm,
    LogExpInstruction,
)
from mmul_gen.machine import INTEGER
from mmul_gen.mixed_math import MixedMathOperation
from mmul_gen.templates.float_mixed_format import FloatMixedFormat
from mmul_gen.templates.logexp_unsupported_source import (
    LogExpUnsupportedSource,
)

class Mlog2Ew(LogExpInstruction):
    """Base-2 logarithm of each element."""

    name = "mlog2.ew"
    summary = "base-2 logarithm of each element"
    subject = "integer log/exp test cases."
    operands = (DESTINATION_OPERAND, FIRST_SOURCE_OPERAND)
    templates = (
        # v0.6 §6.2.2 makes the source and the destination floating point but
        # never asks them to share a format, so a mixed tuple runs.
        FloatMixedFormat(MixedMathOperation.LOG2),
        LogExpUnsupportedSource(
            src1_label="pow2_square", form=LogExpForm.UNARY, domain=INTEGER
        ),
    )

__all__ = ["Mlog2Ew"]
