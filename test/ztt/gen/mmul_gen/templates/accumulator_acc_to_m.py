#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""An accumulator read back into an M register carries the zeroed image.

Same emitted operation as the ``zero_acc`` template because the accumulator is
primed with ``mzero.2d.acc`` before the move; the two differ in the input label
they report.
"""

from __future__ import annotations

DOC_ZH = """\
累加器读回 M 寄存器后仍是清零后的镜像。

与 ``zero_acc`` 模板发射相同的操作，因为搬移前用 ``mzero.2d.acc`` 给累加器播种；两者只是报告的输入标签不同。
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


class AccumulatorAccToM(AccumulatorUtilityTemplate):
    """An accumulator read back into an M register carries the zeroed image."""

    summary_zh = "累加器读回 M 寄存器后仍是清零后的镜像。"
    name = "acc_to_m"
    uses_accumulator = True

    def operation_lines(
        self, instruction: Instruction, layout: RegisterLayout, destination_label: str
    ) -> list[str]:
        return zero_acc_then_copy_out(
            register("md", layout), require_accumulator(layout), destination_label
        )


__all__ = ["AccumulatorAccToM"]


ACCUMULATOR_ACC_TO_M = AccumulatorAccToM()
