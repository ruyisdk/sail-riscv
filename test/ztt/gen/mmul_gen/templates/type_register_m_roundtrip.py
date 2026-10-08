#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""M-register descriptor roundtrip: write the type code, read it back.

Every descriptor the macro file declares is written into an M register and read
back at each legal placement of that register in the M-register file, so one
case covers both the encoding of the descriptor and where the register sits.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from mmul_gen.case_description import description
from mmul_gen.machine import DType, EVERY_DTYPE, MachineConfig
from mmul_gen.registers import MRegisterRole, RegisterLayout, m_register_layouts
from mmul_gen.templates.base import Case, CaseOutput, Template

if TYPE_CHECKING:
    from mmul_gen.instruction import Instruction


class MTypeRoundtrip(Template):
    """Write the descriptor into an M register and read it back."""

    name = "supported_dtype_roundtrip"
    dtypes = EVERY_DTYPE

    def __init__(self, action: str) -> None:
        """``action`` is the prose the case header states for this instruction."""

        self.action = action

    def build(
        self, machine: MachineConfig, instruction: Instruction, dtype: DType
    ) -> Sequence[Case]:
        roles = (MRegisterRole("m", machine.nregs(dtype.bits)),)
        return [
            Case(
                number=0,
                dtype=dtype,
                layout=RegisterLayout(m=layout),
                description=description(self.name),
            )
            for layout in m_register_layouts(machine.num_m_regs, roles)
        ]

    def render(
        self,
        machine: MachineConfig,
        instruction: Instruction,
        case: Case,
        out: CaseOutput,
    ) -> None:
        base = case.layout.group_base("m")
        out.text.extend(
            [
                f"    # case {case.number}: {self.action}: {case.dtype.name}",
                f"    li      t0, {case.dtype.name}",
                f"    msettyp m{base}, t0",
                f"    mgettyp t1, m{base}",
                f"    EXPECT  t1, {case.dtype.name}",
                "",
            ]
        )


__all__ = ["MTypeRoundtrip"]
