#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Saturating case of the in-place power-of-two raise.

Exponentiating a wide value in place overflows the narrow descriptor, which is
exactly the situation the saturating variant exists for: the result clamps and
``amexsat`` reports it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mmul_gen.asm import repeated_square_lines
from mmul_gen.machine import MachineConfig
from mmul_gen.templates.logexp_common import DESTINATION_REGISTER
from mmul_gen.templates.logexp_saturating_common import SaturatingLogExpTemplate

if TYPE_CHECKING:
    from mmul_gen.instructions.logexp.base import LogExpInstruction
    from mmul_gen.machine import DType


class Exp2SaturatingBoundary(SaturatingLogExpTemplate):
    """Raise two to a power that the descriptor cannot hold."""

    name = "exp2_saturating_boundary"

    def saturating_operand_lines(
        self,
        machine: MachineConfig,
        instruction: LogExpInstruction,
        dtype: DType,
        prefix: str,
    ) -> list[str]:
        source_label = f"{prefix}exp_square"
        return [
            f"    la      t1, {source_label}",
            f"    mls.rm     m{DESTINATION_REGISTER}, t1",
            f"    {instruction.name} m{DESTINATION_REGISTER}, m{DESTINATION_REGISTER}",
        ]

    def saturating_data_lines(
        self,
        machine: MachineConfig,
        instruction: LogExpInstruction,
        dtype: DType,
        prefix: str,
    ) -> list[str]:
        # The exponent is the element width itself, so the result is 2**bits:
        # always unrepresentable, and always by more than one step.
        return repeated_square_lines(
            f"{prefix}exp_square", dtype.bits, dtype.bits, machine
        )


__all__ = ["Exp2SaturatingBoundary"]
