#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Generator for ``mzero.2d.acc``: accumulator utility."""

from __future__ import annotations

from mmul_gen.instruction import (
    ACCUMULATOR_OPERAND,
    Instruction,
)
from mmul_gen.templates.accumulator_zero_acc import (
    ACCUMULATOR_ZERO_ACC,
)


class Mzero2dAcc(Instruction):
    """Zero one accumulator and prove the accumulator file came out clean."""

    name = "mzero.2d.acc"
    summary = "zero one accumulator and prove the accumulator file came out clean"
    summary_zh = "将一个累加器清零，并验证整个累加器文件保持干净"
    subject = "accumulator test cases."
    operands = (ACCUMULATOR_OPERAND,)
    templates = (ACCUMULATOR_ZERO_ACC,)


__all__ = ["Mzero2dAcc"]
