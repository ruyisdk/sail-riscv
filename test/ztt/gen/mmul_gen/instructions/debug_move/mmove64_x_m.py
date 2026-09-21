#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Generator for ``mmove64.x.m``: debug scalar/M-register move."""

from __future__ import annotations

from mmul_gen.instruction import (
    M_TRANSFER_OPERAND,
    SCALAR_DESTINATION_OPERAND,
    SCALAR_POSITION_OPERAND,
    Instruction,
)
from mmul_gen.templates.debug_move64 import (
    DEBUG_MOVE64,
)


class Mmove64XM(Instruction):
    """Read one 64-bit scalar back out of an m register element."""

    name = "mmove64.x.m"
    summary = "read one 64-bit scalar back out of an M register element"
    summary_zh = "从 M 寄存器的指定元素读回一个 64 位标量"
    subject = "debug move semantic test cases."
    operands = (SCALAR_DESTINATION_OPERAND, M_TRANSFER_OPERAND, SCALAR_POSITION_OPERAND)
    templates = (DEBUG_MOVE64,)


__all__ = ["Mmove64XM"]
