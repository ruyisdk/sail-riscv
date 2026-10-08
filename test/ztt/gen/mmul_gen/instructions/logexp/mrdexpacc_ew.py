#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Generator for ``mrdexpacc.ew``: integer log/exp."""

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

class MrdexpaccEw(LogExpInstruction):
    """Accumulate a reconstructed mantissa."""

    name = "mrdexpacc.ew"
    summary = "accumulate a reconstructed mantissa"
    subject = "integer log/exp test cases."
    operands = (DESTINATION_OPERAND, FIRST_SOURCE_OPERAND, SECOND_SOURCE_OPERAND)
    templates = (
        LogExpNominal( src1_label="rd_mant_square", expected=11, form=LogExpForm.TERNARY_M, src2_label="exp_square2", initialize_destination=True, ),
    )

__all__ = ["MrdexpaccEw"]
