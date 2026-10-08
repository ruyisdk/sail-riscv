#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Generator for ``mlog2sub.ew``: integer log/exp."""

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

class Mlog2subEw(LogExpInstruction):
    """Base-2 logarithm of the ratio of two squares."""

    name = "mlog2sub.ew"
    summary = "base-2 logarithm of the ratio of two squares"
    subject = "integer log/exp test cases."
    operands = (DESTINATION_OPERAND, FIRST_SOURCE_OPERAND, SECOND_SOURCE_OPERAND)
    templates = (
        LogExpNominal( src1_label="pow2_square", expected=1, form=LogExpForm.BINARY_M, src2_label="exp_square2", ),
    )

__all__ = ["Mlog2subEw"]
