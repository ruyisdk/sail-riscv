#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Generator for ``mexp2.ew``: integer log/exp."""

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
from mmul_gen.templates.logexp_saturating_exp2 import (
    Exp2SaturatingBoundary,
)
from mmul_gen.templates.logexp_saturating_exp2_wide import (
    Exp2Saturating128,
)

class Mexp2Ew(LogExpInstruction):
    """Raise two to each element's exponent."""

    name = "mexp2.ew"
    summary = "raise two to each element's exponent"
    subject = "integer log/exp test cases."
    operands = (DESTINATION_OPERAND, FIRST_SOURCE_OPERAND)
    templates = (
        LogExpNominal(src1_label="exp_square", expected=8, form=LogExpForm.UNARY),
        Exp2SaturatingBoundary(form=LogExpForm.UNARY),
        Exp2Saturating128(form=LogExpForm.UNARY),
    )

__all__ = ["Mexp2Ew"]
