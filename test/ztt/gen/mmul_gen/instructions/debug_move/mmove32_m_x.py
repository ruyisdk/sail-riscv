#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Generator for ``mmove32.m.x``: debug scalar/M-register move."""

from __future__ import annotations

from mmul_gen.instruction import (
    M_TRANSFER_OPERAND,
    SCALAR_POSITION_OPERAND,
    SCALAR_SOURCE_OPERAND,
    Instruction,
)
from mmul_gen.templates.debug_move32 import (
    DEBUG_MOVE32,
)


class Mmove32MX(Instruction):
    """Write one 32-bit scalar into an m register at an element position."""

    name = "mmove32.m.x"
    summary = "write one 32-bit scalar into an M register at an element position"
    summary_zh = "将一个 32 位标量写入 M 寄存器的指定元素位置"
    subject = "debug move semantic test cases."
    operands = (M_TRANSFER_OPERAND, SCALAR_SOURCE_OPERAND, SCALAR_POSITION_OPERAND)
    templates = (DEBUG_MOVE32,)


__all__ = ["Mmove32MX"]
