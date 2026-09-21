#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Zeroing an M register must leave an all-zero square once stored.

This is the only instruction of the family that addresses no accumulator, so
its cases carry an M layout and no ACC layout.
"""

from __future__ import annotations

DOC_ZH = """\
将 M 寄存器清零后存储出来，结果必须是全零方阵。

这是该家族中唯一不寻址累加器的指令，因此它的用例只携带 M 布局，没有 ACC 布局。
"""

from typing import TYPE_CHECKING

from mmul_gen.registers import RegisterLayout
from mmul_gen.templates.accumulator_common import (
    AccumulatorUtilityTemplate,
    zero_m_then_copy_out,
)
from mmul_gen.templates.base import register

if TYPE_CHECKING:
    from mmul_gen.instruction import Instruction


class AccumulatorZeroM(AccumulatorUtilityTemplate):
    """Zeroing an M register must leave an all-zero square once stored."""

    summary_zh = "将 M 寄存器清零后存储出来，结果必须是全零方阵。"
    name = "zero_m"
    uses_accumulator = False

    def operation_lines(
        self, instruction: Instruction, layout: RegisterLayout, destination_label: str
    ) -> list[str]:
        return zero_m_then_copy_out(register("md", layout), destination_label)


__all__ = ["AccumulatorZeroM"]


ACCUMULATOR_ZERO_M = AccumulatorZeroM()
