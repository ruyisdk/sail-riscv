#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Generator for ``msublog2.ew.x``: integer log/exp."""

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

class Msublog2EwX(LogExpInstruction):
    """Scalar base-2 logarithm of a difference."""

    name = "msublog2.ew.x"
    summary = "scalar base-2 logarithm of a difference"
    summary_zh = "对标量差值取以 2 为底的对数"
    subject = "integer log/exp test cases."
    operands = (DESTINATION_OPERAND, SCALAR_SOURCE_OPERAND, FIRST_SOURCE_OPERAND)
    templates = (
        LogExpNominal( src1_label="pow2_square", expected=7, form=LogExpForm.BINARY_X, scalar=10, scalar_dtype_csr=True, ),
    )

__all__ = ["Msublog2EwX"]
