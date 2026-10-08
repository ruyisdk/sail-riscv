#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Generator for ``mmove32.x.m``: debug scalar/M-register move."""

from __future__ import annotations

from mmul_gen.instruction import (
    M_TRANSFER_OPERAND,
    SCALAR_DESTINATION_OPERAND,
    SCALAR_POSITION_OPERAND,
    Instruction,
)
from mmul_gen.templates.debug_move32 import (
    DEBUG_MOVE32,
)


class Mmove32XM(Instruction):
    """Read one 32-bit scalar back out of an m register element."""

    name = "mmove32.x.m"
    summary = "read one 32-bit scalar back out of an M register element"
    subject = "debug move semantic test cases."
    operands = (SCALAR_DESTINATION_OPERAND, M_TRANSFER_OPERAND, SCALAR_POSITION_OPERAND)
    templates = (DEBUG_MOVE32,)


__all__ = ["Mmove32XM"]
