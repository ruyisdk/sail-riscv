#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Replicate one source column across every column of each row.

Broadcasting the first column proves the operand is read by row, broadcasting
the last one also proves the row stride is the active length rather than a
compile-time constant.
"""

from __future__ import annotations

DOC_ZH = """\
将源方阵的某一列复制到每一行的所有列。

广播第一列证明操作数按行读取，广播最后一列还证明行步长取的是有效长度而不是编译期常量。
"""

from collections.abc import Sequence
from typing import TYPE_CHECKING

from mmul_gen.machine import MachineConfig
from mmul_gen.templates.axis_permute_common import (
    AxisPermuteTemplate,
)

if TYPE_CHECKING:
    from mmul_gen.instruction import Instruction


class ColumnBroadcast(AxisPermuteTemplate):
    """Replicate one source column across every column of each row."""

    summary_zh = "将源方阵的某一列复制到每一行的所有列。"
    name = "column_broadcast"
    input_cases = ("first_column", "last_column")

    def expected_values(
        self, machine: MachineConfig, source: Sequence[int], input_case: str
    ) -> list[int]:
        index = 0 if input_case == "first_column" else machine.n - 1
        return [
            source[row * machine.n + index]
            for row in range(machine.n)
            for _col in range(machine.n)
        ]

    def operand_lines(
        self,
        machine: MachineConfig,
        instruction: Instruction,
        input_case: str,
        destination: int,
    ) -> list[str]:
        index = 0 if input_case == "first_column" else machine.n - 1
        return [f"    li      t4, {index}", f"    {instruction.name} m{destination}, t4, m0"]


__all__ = ["ColumnBroadcast"]


COLUMN_BROADCAST = ColumnBroadcast()
