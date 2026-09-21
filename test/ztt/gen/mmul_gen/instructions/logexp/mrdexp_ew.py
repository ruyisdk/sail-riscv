#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Generator for ``mrdexp.ew``: integer log/exp."""

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

class MrdexpEw(LogExpInstruction):
    """Recover the mantissa of a scaled square."""

    name = "mrdexp.ew"
    summary = "recover the mantissa of a scaled square"
    summary_zh = "恢复已缩放方阵的尾数"
    subject = "integer log/exp test cases."
    operands = (DESTINATION_OPERAND, FIRST_SOURCE_OPERAND, SECOND_SOURCE_OPERAND)
    templates = (
        LogExpNominal( src1_label="rd_mant_square", expected=4, form=LogExpForm.BINARY_M, src2_label="exp_square2", ),
    )

__all__ = ["MrdexpEw"]
