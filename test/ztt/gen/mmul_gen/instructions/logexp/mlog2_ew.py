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
from mmul_gen.templates.logexp_nominal import (
    LogExpNominal,
)

class Mlog2Ew(LogExpInstruction):
    """Base-2 logarithm of each element."""

    name = "mlog2.ew"
    summary = "base-2 logarithm of each element"
    summary_zh = "对每个元素取以 2 为底的对数"
    subject = "integer log/exp test cases."
    operands = (DESTINATION_OPERAND, FIRST_SOURCE_OPERAND)
    templates = (
        LogExpNominal(src1_label="pow2_square", expected=3, form=LogExpForm.UNARY),
    )

__all__ = ["Mlog2Ew"]
