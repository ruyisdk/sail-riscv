#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Generator for ``mldexpacc.ew.x``: integer log/exp."""

from __future__ import annotations

from mmul_gen.instruction import (
    DESTINATION_OPERAND,
    FIRST_SOURCE_OPERAND,
    SCALAR_SOURCE_OPERAND,
)
from mmul_gen.instructions.logexp.base import (
    LogExpForm,
    LogExpInstruction,
)
from mmul_gen.templates.logexp_nominal import (
    LogExpNominal,
)

class MldexpaccEwX(LogExpInstruction):
    """Accumulate a mantissa square scaled by one scalar exponent."""

    name = "mldexpacc.ew.x"
    summary = "accumulate a mantissa square scaled by one scalar exponent"
    summary_zh = "累加按同一标量指数缩放的尾数方阵"
    subject = "integer log/exp test cases."
    operands = (DESTINATION_OPERAND, SCALAR_SOURCE_OPERAND, FIRST_SOURCE_OPERAND)
    templates = (
        LogExpNominal( src1_label="mant_square", expected=13, form=LogExpForm.BINARY_X, scalar=1, initialize_destination=True, ),
    )

__all__ = ["MldexpaccEwX"]
