#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Generator for ``mmove16.m.x``: debug scalar/M-register move."""

from __future__ import annotations

from mmul_gen.instruction import (
    M_TRANSFER_OPERAND,
    SCALAR_POSITION_OPERAND,
    SCALAR_SOURCE_OPERAND,
    Instruction,
)
from mmul_gen.templates.debug_move16 import (
    DEBUG_MOVE16,
)


class Mmove16MX(Instruction):
    """Write one 16-bit scalar into an m register at an element position."""

    name = "mmove16.m.x"
    summary = "write one 16-bit scalar into an M register at an element position"
    subject = "debug move semantic test cases."
    operands = (M_TRANSFER_OPERAND, SCALAR_SOURCE_OPERAND, SCALAR_POSITION_OPERAND)
    templates = (DEBUG_MOVE16,)


__all__ = ["Mmove16MX"]
