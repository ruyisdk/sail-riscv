#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Accumulator descriptor roundtrip: write the type code, read it back.

Every descriptor the macro file declares is written into every accumulator the
configuration provides and read back, so the roundtrip covers the whole
accumulator file rather than a sample of it.
"""

from __future__ import annotations

DOC_ZH = """\
累加器描述符往返：写入类型编码，再读回。

宏文件声明的每个描述符都被写入配置提供的每个累加器并读回，因此往返覆盖整个累加器文件，而不是其中的抽样。
"""

from collections.abc import Sequence
from typing import TYPE_CHECKING

from mmul_gen.case_description import description_zh
from mmul_gen.machine import DType, EVERY_DTYPE, MachineConfig
from mmul_gen.registers import RegisterLayout, accumulator_operands
from mmul_gen.templates.base import Case, CaseOutput, Template

if TYPE_CHECKING:
    from mmul_gen.instruction import Instruction


class AccTypeRoundtrip(Template):
    """Write the descriptor into an accumulator and read it back."""

    summary_zh = "将描述符写入累加器再读回，验证往返一致。"
    name = "supported_dtype_roundtrip"
    dtypes = EVERY_DTYPE

    def __init__(self, action: str) -> None:
        """``action`` is the prose the case header states for this instruction."""

        self.action = action

    def build(
        self, machine: MachineConfig, instruction: Instruction, dtype: DType
    ) -> Sequence[Case]:
        return [
            Case(
                number=0,
                dtype=dtype,
                layout=RegisterLayout(acc=operand),
                description=description_zh(self.name),
            )
            for operand in accumulator_operands(machine.num_acc_regs)
        ]

    def render(
        self,
        machine: MachineConfig,
        instruction: Instruction,
        case: Case,
        out: CaseOutput,
    ) -> None:
        base = case.layout.acc_base()
        out.text.extend(
            [
                f"    # case {case.number}: {self.action}: {case.dtype.name}",
                f"    li      t0, {case.dtype.name}",
                f"    asettyp acc{base}, t0",
                f"    agettyp t1, acc{base}",
                f"    EXPECT  t1, {case.dtype.name}",
                "",
            ]
        )


__all__ = ["AccTypeRoundtrip"]
