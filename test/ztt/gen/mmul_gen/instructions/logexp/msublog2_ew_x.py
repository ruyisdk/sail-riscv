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
from mmul_gen.machine import INTEGER
from mmul_gen.templates.logexp_unsupported_source import (
    LogExpUnsupportedSource,
)

class Msublog2EwX(LogExpInstruction):
    """Scalar base-2 logarithm of a difference."""

    name = "msublog2.ew.x"
    summary = "scalar base-2 logarithm of a difference"
    subject = "integer log/exp test cases."
    operands = (DESTINATION_OPERAND, SCALAR_SOURCE_OPERAND, FIRST_SOURCE_OPERAND)
    templates = (
        LogExpUnsupportedSource(
            src1_label="pow2_square",
            form=LogExpForm.BINARY_X,
            domain=INTEGER,
            scalar=10,
            scalar_dtype_csr=True,
        ),
    )

__all__ = ["Msublog2EwX"]
