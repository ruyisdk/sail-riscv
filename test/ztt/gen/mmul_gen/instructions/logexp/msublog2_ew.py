#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Generator for ``msublog2.ew``: integer log/exp."""

from __future__ import annotations

from mmul_gen.instruction import (
    DESTINATION_OPERAND,
    FIRST_SOURCE_OPERAND,
    SECOND_SOURCE_OPERAND,
)
from mmul_gen.instructions.logexp.base import (
    LogExpForm,
    LogExpInstruction,
)
from mmul_gen.templates.logexp_nominal import (
    LogExpNominal,
)

class Msublog2Ew(LogExpInstruction):
    """Base-2 logarithm of a difference of squares."""

    name = "msublog2.ew"
    summary = "base-2 logarithm of a difference of squares"
    subject = "integer log/exp test cases."
    operands = (DESTINATION_OPERAND, FIRST_SOURCE_OPERAND, SECOND_SOURCE_OPERAND)
    templates = (
        LogExpNominal( src1_label="pow2_square", expected=7, form=LogExpForm.BINARY_M, src2_label="bias_square", ),
    )

__all__ = ["Msublog2Ew"]
