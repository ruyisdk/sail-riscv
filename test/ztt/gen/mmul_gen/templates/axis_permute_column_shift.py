#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Shift every row by one column, dropping what leaves the active square.

Shifting forward and in reverse proves both edges: the column that leaves the
active square must read as zero, which is what the in-range test in the
expected-value walk encodes.
"""

from __future__ import annotations

DOC_ZH = """\
将每一行平移一列，移出有效方阵的部分被丢弃。

正向与反向平移共同证明两条边界：移出有效方阵的列必须读为 0，这正是期望值遍历中范围判断所编码的内容。
"""

from collections.abc import Sequence
from typing import TYPE_CHECKING

from mmul_gen.machine import MachineConfig
from mmul_gen.templates.axis_permute_common import (
    FORWARD_SHIFT,
    REVERSE_SHIFT,
    AxisPermuteTemplate,
)

if TYPE_CHECKING:
    from mmul_gen.instruction import Instruction


class ColumnShift(AxisPermuteTemplate):
    """Shift every row by one column, dropping what leaves the active square."""

    summary_zh = "将每一行平移一列，移出有效方阵的部分被丢弃。"
    name = "column_shift"
    input_cases = ("forward_shift", "reverse_shift")

    def expected_values(
        self, machine: MachineConfig, source: Sequence[int], input_case: str
    ) -> list[int]:
        shift = FORWARD_SHIFT if input_case == "forward_shift" else REVERSE_SHIFT
        values = []
        for row in range(machine.n):
            for col in range(machine.n):
                source_col = col + shift
                values.append(
                    source[row * machine.n + source_col]
                    if 0 <= source_col < machine.n
                    else 0
                )
        return values

    def operand_lines(
        self,
        machine: MachineConfig,
        instruction: Instruction,
        input_case: str,
        destination: int,
    ) -> list[str]:
        shift = FORWARD_SHIFT if input_case == "forward_shift" else REVERSE_SHIFT
        return [f"    li      t4, {shift}", f"    {instruction.name} m{destination}, t4, m0"]


__all__ = ["ColumnShift"]


COLUMN_SHIFT = ColumnShift()
