#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Generator for ``mldexp.ew``: integer log/exp."""

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

class MldexpEw(LogExpInstruction):
    """Scale a mantissa square by a per-element power of two."""

    name = "mldexp.ew"
    summary = "scale a mantissa square by a per-element power of two"
    summary_zh = "按每个元素各自的 2 的幂缩放尾数方阵"
    subject = "integer log/exp test cases."
    operands = (DESTINATION_OPERAND, FIRST_SOURCE_OPERAND, SECOND_SOURCE_OPERAND)
    templates = (
        LogExpNominal( src1_label="mant_square", expected=12, form=LogExpForm.BINARY_M, src2_label="exp_square2", ),
    )

__all__ = ["MldexpEw"]
