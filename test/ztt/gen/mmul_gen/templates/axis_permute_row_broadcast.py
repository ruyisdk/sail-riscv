#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Replicate one source row across every row of each column.

Broadcasting the first row proves the operand is read by column, broadcasting
the last one also proves the row stride is the active length rather than a
compile-time constant.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from mmul_gen.machine import MachineConfig
from mmul_gen.templates.axis_permute_common import (
    AxisPermuteTemplate,
)

if TYPE_CHECKING:
    from mmul_gen.instruction import Instruction


class RowBroadcast(AxisPermuteTemplate):
    """Replicate one source row across every row of each column."""

    name = "row_broadcast"
    input_cases = ("first_row", "last_row")

    def expected_values(
        self, machine: MachineConfig, source: Sequence[int], input_case: str
    ) -> list[int]:
        index = 0 if input_case == "first_row" else machine.n - 1
        return [
            source[index * machine.n + col]
            for _row in range(machine.n)
            for col in range(machine.n)
        ]

    def operand_lines(
        self,
        machine: MachineConfig,
        instruction: Instruction,
        input_case: str,
        destination: int,
    ) -> list[str]:
        index = 0 if input_case == "first_row" else machine.n - 1
        return [f"    li      t4, {index}", f"    {instruction.name} m{destination}, t4, m0"]


__all__ = ["RowBroadcast"]


ROW_BROADCAST = RowBroadcast()
