#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Generator for ``mmov.m.a``: accumulator utility."""

from __future__ import annotations

from mmul_gen.instruction import (
    ACCUMULATOR_OPERAND,
    DESTINATION_OPERAND,
    Instruction,
)
from mmul_gen.templates.accumulator_acc_to_m import (
    ACCUMULATOR_ACC_TO_M,
)


class MmovMA(Instruction):
    """Copy one accumulator into an m register."""

    name = "mmov.m.a"
    summary = "copy one accumulator into an M register"
    summary_zh = "将一个累加器拷贝到 M 寄存器"
    subject = "accumulator test cases."
    operands = (DESTINATION_OPERAND, ACCUMULATOR_OPERAND)
    templates = (ACCUMULATOR_ACC_TO_M,)


__all__ = ["MmovMA"]
