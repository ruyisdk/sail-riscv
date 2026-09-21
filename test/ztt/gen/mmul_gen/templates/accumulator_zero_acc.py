#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Zeroing an accumulator and copying it out must leave an all-zero square.

The copy is what makes the check meaningful: it reads the accumulator back
through ``mmov.m.a``, so a zeroed descriptor with a stale payload still fails.
"""

from __future__ import annotations

DOC_ZH = """\
将累加器清零再拷贝出来，结果必须是全零方阵。

拷贝才让检查有意义：它通过 ``mmov.m.a`` 把累加器读回，因此描述符已清零但载荷陈旧的实现仍会失败。
"""

from typing import TYPE_CHECKING

from mmul_gen.registers import RegisterLayout
from mmul_gen.templates.accumulator_common import (
    AccumulatorUtilityTemplate,
    require_accumulator,
    zero_acc_then_copy_out,
)
from mmul_gen.templates.base import register

if TYPE_CHECKING:
    from mmul_gen.instruction import Instruction


class AccumulatorZeroAcc(AccumulatorUtilityTemplate):
    """Zeroing an accumulator and copying it out must leave an all-zero square."""

    summary_zh = "将累加器清零再拷贝出来，结果必须是全零方阵。"
    name = "zero_acc"
    uses_accumulator = True

    def operation_lines(
        self, instruction: Instruction, layout: RegisterLayout, destination_label: str
    ) -> list[str]:
        return zero_acc_then_copy_out(
            register("md", layout), require_accumulator(layout), destination_label
        )


__all__ = ["AccumulatorZeroAcc"]


ACCUMULATOR_ZERO_ACC = AccumulatorZeroAcc()
