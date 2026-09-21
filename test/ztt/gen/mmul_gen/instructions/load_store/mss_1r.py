#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Generator for ``mss.1r``: raw store of one physical M register."""

from __future__ import annotations

from mmul_gen.instruction import (
    M_TRANSFER_OPERAND,
    SCALAR_DESTINATION_OPERAND,
    Instruction,
)
from mmul_gen.templates.raw_transfer import (
    RAW_TRANSFER,
)


class Mss1r(Instruction):
    """M register read by the store."""

    name = "mss.1r"
    summary = "store one physical M register to memory"
    summary_zh = "将一个物理 M 寄存器存入内存"
    subject = "raw load/store test cases."
    operands = (M_TRANSFER_OPERAND, SCALAR_DESTINATION_OPERAND)
    templates = (RAW_TRANSFER,)


__all__ = ["Mss1r"]
