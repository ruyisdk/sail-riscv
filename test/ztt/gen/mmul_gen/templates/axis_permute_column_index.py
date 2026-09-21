#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Fill every element with its own column coordinate.

The source ramp is loaded but not read: the expected square is the column index
itself, so a wrong active length shows up as a wrong coordinate, not as a
missing element.
"""

from __future__ import annotations

DOC_ZH = """\
以元素的列坐标填充每个元素。

源斜坡被加载但不被读取：期望方阵就是列索引本身，因此有效长度错误会表现为坐标错误，而不是缺少元素。
"""

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

    summary_zh = "以元素的列坐标填充每个元素。"
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
