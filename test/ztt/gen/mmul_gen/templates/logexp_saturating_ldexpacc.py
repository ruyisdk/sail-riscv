#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Saturating case of the scaled accumulate.

Accumulating a scaled representable value into a destination seeded with the
largest representable value overflows by construction, so the accumulate form
reaches saturation through its accumulator rather than through its exponent.
"""

from __future__ import annotations

DOC_ZH = """\
缩放累加的饱和用例。

把一个可表示值缩放后累加进以最大可表示值播种的目的方阵，按构造就会上溢，因此累加形式通过累加器而不是指数到达饱和。
"""

from typing import TYPE_CHECKING

from mmul_gen.asm import repeated_square_lines
from mmul_gen.machine import MachineConfig
from mmul_gen.templates.logexp_common import DESTINATION_REGISTER, source_registers
from mmul_gen.templates.logexp_saturating_common import (
    SaturatingLogExpTemplate,
    clamped_square,
)

if TYPE_CHECKING:
    from mmul_gen.instructions.logexp.base import LogExpInstruction
    from mmul_gen.machine import DType


class LdexpaccSaturatingBoundary(SaturatingLogExpTemplate):
    """Accumulate a scaled mantissa into a maximal accumulator."""

    summary_zh = "将缩放后的尾数累加进已达最大值的累加器。"
    name = "ldexpacc_saturating_boundary"

    def saturating_operand_lines(
        self,
        machine: MachineConfig,
        instruction: LogExpInstruction,
        dtype: DType,
        prefix: str,
    ) -> list[str]:
        src1_reg, src2_reg = source_registers(machine, dtype.bits)
        return [
            f"    la      t1, {prefix}max_square",
            f"    mls.rm     m{DESTINATION_REGISTER}, t1",
            f"    la      t2, {prefix}one_square",
            f"    mls.rm     m{src1_reg}, t2",
            f"    la      t3, {prefix}exp_one_square",
            f"    mls.rm     m{src2_reg}, t3",
            f"    {instruction.name} m{DESTINATION_REGISTER}, m{src1_reg}, m{src2_reg}",
        ]

    def saturating_data_lines(
        self,
        machine: MachineConfig,
        instruction: LogExpInstruction,
        dtype: DType,
        prefix: str,
    ) -> list[str]:
        return [
            *clamped_square(machine, dtype, prefix, "max_square"),
            *repeated_square_lines(f"{prefix}one_square", 1, dtype.bits, machine),
            *repeated_square_lines(f"{prefix}exp_one_square", 1, dtype.bits, machine),
        ]


__all__ = ["LdexpaccSaturatingBoundary"]
