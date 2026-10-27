#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Fill every element with its own column coordinate.

Spec:    instructions.adoc:1130-1131 (§6.26)
Quote:   "Writes to each element of the M register group `md` the zero-based index of the column
         containing that element."
Checks:  mcolid.ew must write each element's own column coordinate into the destination square, so
         a mis-formed active length shows up as a wrong coordinate, not as a missing element.

The source ramp is loaded but not read: the expected square is the column index
itself, so a wrong active length shows up as a wrong coordinate, not as a
missing element.
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


class ColumnIndex(AxisPermuteTemplate):
    """Fill every element with its own column coordinate."""

    name = "column_index"
    input_cases = ("coordinate_ramp",)

    def expected_values(
        self, machine: MachineConfig, source: Sequence[int], input_case: str
    ) -> list[int]:
        return [col for _row in range(machine.n) for col in range(machine.n)]

    def operand_lines(
        self,
        machine: MachineConfig,
        instruction: Instruction,
        input_case: str,
        destination: int,
    ) -> list[str]:
        return [f"    {instruction.name} m{destination}"]


__all__ = ["ColumnIndex"]


COLUMN_INDEX = ColumnIndex()
