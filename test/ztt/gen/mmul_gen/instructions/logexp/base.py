#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Shared declaration of the integer log/exp family.

One integer log/exp instruction and the ``.data`` footer every one of them
carries.  Which squares an instruction reads, what it expects, and which operand
shape it has are not declared here: they are the arguments of its templates.
"""

from __future__ import annotations

from mmul_gen.asm import dst_square_lines
from mmul_gen.instruction import Instruction
from mmul_gen.machine import MachineConfig
from mmul_gen.templates.logexp_common import LogExpForm


class LogExpInstruction(Instruction, family_base=True):
    """One integer log/exp instruction.

    The labels, the expected value and the operand shape name squares and shapes
    defined by :mod:`mmul_gen.templates.logexp_common`; passing them to the
    templates is what lets one nominal template serve all twelve instructions.
    """

    def data_footer(self, machine: MachineConfig) -> list[str]:
        """Every log/exp source ends with the shared scratch square."""

        return dst_square_lines(machine)

__all__ = [
    "LogExpForm",
    "LogExpInstruction",
]
