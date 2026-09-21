#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Generator for ``mmove16.x.m``: debug scalar/M-register move."""

from __future__ import annotations

from mmul_gen.instruction import (
    M_TRANSFER_OPERAND,
    SCALAR_DESTINATION_OPERAND,
    SCALAR_POSITION_OPERAND,
    Instruction,
)
from mmul_gen.templates.debug_move16 import (
    DEBUG_MOVE16,
)


class Mmove16XM(Instruction):
    """Read one 16-bit scalar back out of an m register element."""

    name = "mmove16.x.m"
    summary = "read one 16-bit scalar back out of an M register element"
    summary_zh = "从 M 寄存器的指定元素读回一个 16 位标量"
    subject = "debug move semantic test cases."
    operands = (SCALAR_DESTINATION_OPERAND, M_TRANSFER_OPERAND, SCALAR_POSITION_OPERAND)
    templates = (DEBUG_MOVE16,)


__all__ = ["Mmove16XM"]
