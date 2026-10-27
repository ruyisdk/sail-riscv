#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Generator for ``mlog2sub.ew.x``: integer log/exp."""

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
from mmul_gen.machine import INTEGER
from mmul_gen.templates.log2bias_tuple import (
    Log2BiasTuple,
)
from mmul_gen.templates.logexp_unsupported_source import (
    LogExpUnsupportedSource,
)

class Mlog2subEwX(LogExpInstruction):
    """Scalar base-2 logarithm of a ratio."""

    name = "mlog2sub.ew.x"
    summary = "scalar base-2 logarithm of a ratio"
    subject = "integer log/exp test cases."
    operands = (DESTINATION_OPERAND, SCALAR_SOURCE_OPERAND, FIRST_SOURCE_OPERAND)
    templates = (
        LogExpUnsupportedSource(
            src1_label="pow2_square",
            form=LogExpForm.BINARY_X,
            domain=INTEGER,
            scalar=1,
            scalar_dtype_csr=True,
        ),
        Log2BiasTuple(log_minus_bias=True, form=LogExpForm.BINARY_X),
    )

__all__ = ["Mlog2subEwX"]
