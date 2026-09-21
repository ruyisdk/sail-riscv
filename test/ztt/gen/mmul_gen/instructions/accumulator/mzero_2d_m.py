#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Generator for ``mzero.2d.m``: accumulator utility."""

from __future__ import annotations

from mmul_gen.instruction import (
    DESTINATION_OPERAND,
    Instruction,
)
from mmul_gen.templates.accumulator_zero_m import (
    ACCUMULATOR_ZERO_M,
)


class Mzero2dM(Instruction):
    """Zero one m register."""

    name = "mzero.2d.m"
    summary = "zero one M register"
    summary_zh = "将一个 M 寄存器清零"
    subject = "accumulator test cases."
    operands = (DESTINATION_OPERAND,)
    templates = (ACCUMULATOR_ZERO_M,)


__all__ = ["Mzero2dM"]
