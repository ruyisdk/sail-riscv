#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Generator for ``mmov.a.m``: accumulator utility."""

from __future__ import annotations

from mmul_gen.instruction import (
    ACCUMULATOR_OPERAND,
    Instruction,
    M_TRANSFER_OPERAND,
)
from mmul_gen.templates.accumulator_m_to_acc import (
    ACCUMULATOR_M_TO_ACC,
)


class MmovAM(Instruction):
    """Copy one m register into an accumulator."""

    name = "mmov.a.m"
    summary = "copy one M register into an accumulator"
    summary_zh = "将一个 M 寄存器拷贝到累加器"
    subject = "accumulator test cases."
    operands = (ACCUMULATOR_OPERAND, M_TRANSFER_OPERAND)
    templates = (ACCUMULATOR_M_TO_ACC,)


__all__ = ["MmovAM"]
