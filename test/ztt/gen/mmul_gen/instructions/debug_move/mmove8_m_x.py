#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Generator for ``mmove8.m.x``: debug scalar/M-register move."""

from __future__ import annotations

from mmul_gen.instruction import (
    M_TRANSFER_OPERAND,
    SCALAR_POSITION_OPERAND,
    SCALAR_SOURCE_OPERAND,
    Instruction,
)
from mmul_gen.templates.debug_move8 import (
    DEBUG_MOVE8,
)


class Mmove8MX(Instruction):
    """Write one 8-bit scalar into an m register at an element position."""

    name = "mmove8.m.x"
    summary = "write one 8-bit scalar into an M register at an element position"
    summary_zh = "将一个 8 位标量写入 M 寄存器的指定元素位置"
    subject = "debug move semantic test cases."
    operands = (M_TRANSFER_OPERAND, SCALAR_SOURCE_OPERAND, SCALAR_POSITION_OPERAND)
    templates = (DEBUG_MOVE8,)


__all__ = ["Mmove8MX"]
