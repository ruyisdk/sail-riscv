#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Generator for ``mldexp.ew.x``: integer log/exp."""

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

class MldexpEwX(LogExpInstruction):
    """Scale a mantissa square by one scalar exponent."""

    name = "mldexp.ew.x"
    summary = "scale a mantissa square by one scalar exponent"
    subject = "integer log/exp test cases."
    operands = (DESTINATION_OPERAND, SCALAR_SOURCE_OPERAND, FIRST_SOURCE_OPERAND)
    templates = (
        LogExpNominal(src1_label="mant_square", expected=6, form=LogExpForm.BINARY_X, scalar=1),
    )

__all__ = ["MldexpEwX"]
