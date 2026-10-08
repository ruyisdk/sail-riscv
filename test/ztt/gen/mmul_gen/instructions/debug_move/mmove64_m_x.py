#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Generator for ``mmove64.m.x``: debug scalar/M-register move."""

from __future__ import annotations

from mmul_gen.instruction import (
    M_TRANSFER_OPERAND,
    SCALAR_POSITION_OPERAND,
    SCALAR_SOURCE_OPERAND,
    Instruction,
)
from mmul_gen.templates.debug_move64 import (
    DEBUG_MOVE64,
)


class Mmove64MX(Instruction):
    """Write one 64-bit scalar into an m register at an element position."""

    name = "mmove64.m.x"
    summary = "write one 64-bit scalar into an M register at an element position"
    subject = "debug move semantic test cases."
    operands = (M_TRANSFER_OPERAND, SCALAR_SOURCE_OPERAND, SCALAR_POSITION_OPERAND)
    templates = (DEBUG_MOVE64,)


__all__ = ["Mmove64MX"]
