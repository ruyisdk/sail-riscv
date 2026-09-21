#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Shared declaration of the matrix-multiply family.

One matrix multiply and the ``.data`` footer its sources carry.  The
transposed/negated shape of the product is not declared here: each instruction
states the :class:`ProductFlags` it forms as the argument of every template it
runs.
"""

from __future__ import annotations

from mmul_gen.asm import dst_square_lines
from mmul_gen.instruction import Instruction
from mmul_gen.machine import MachineConfig


class MatrixMultiplyInstruction(Instruction, family_base=True):
    """Declarative definition of one matrix-multiply instruction."""

    subject = "2D matrix multiply test cases."

    def data_footer(self, machine: MachineConfig) -> list[str]:
        return dst_square_lines(machine)


__all__ = [
    "MatrixMultiplyInstruction",
]
