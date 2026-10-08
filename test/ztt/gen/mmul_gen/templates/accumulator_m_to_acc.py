#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""An M register moved into an accumulator and back keeps the zeroed image.

The destination M register aliases the source one: the accumulator has consumed
the source by the time the result is read back, so the reuse is a real temporal
alias rather than an accidental overlap.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mmul_gen.registers import MRegisterRole, RegisterLayout
from mmul_gen.templates.accumulator_common import (
    AccumulatorUtilityTemplate,
    m_to_acc_then_copy_out,
    require_accumulator,
)
from mmul_gen.templates.base import register

if TYPE_CHECKING:
    from mmul_gen.instruction import Instruction


class AccumulatorMToAcc(AccumulatorUtilityTemplate):
    """An M register moved into an accumulator and back keeps the zeroed image."""

    name = "m_to_acc"
    uses_accumulator = True

    def m_register_roles(self, machine, dtype) -> tuple[MRegisterRole, ...]:
        """The destination aliases the source, which the move has consumed."""

        nregs = machine.nregs(dtype.bits)
        return (
            MRegisterRole("ms", nregs),
            MRegisterRole("md", nregs, reuse_of="ms"),
        )

    def operation_lines(
        self, instruction: Instruction, layout: RegisterLayout, destination_label: str
    ) -> list[str]:
        return m_to_acc_then_copy_out(
            register("ms", layout),
            register("md", layout),
            require_accumulator(layout),
            destination_label,
        )


__all__ = ["AccumulatorMToAcc"]


ACCUMULATOR_M_TO_ACC = AccumulatorMToAcc()
