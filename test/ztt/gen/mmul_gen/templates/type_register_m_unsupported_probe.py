#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""M-register descriptor error probe: an unusable code must change nothing.

The register is first seeded with a descriptor the assembler does define, then
presented with a code outside the encoding.  The status flag must report the
rejected write and the descriptor must still read back as the seed.
"""

from __future__ import annotations

DOC_ZH = """\
M 寄存器描述符错误探针：不可用的编码不得改变任何状态。

寄存器先用汇编器确实定义的描述符播种，再被写入一个编码之外的编码。状态标志必须报告被拒绝的写入，且描述符必须仍读回其播种值。
"""

from collections.abc import Sequence
from typing import TYPE_CHECKING

from mmul_gen.machine import DType, MachineConfig, PROBE_DTYPE
from mmul_gen.registers import MRegisterRole, RegisterLayout, m_register_layouts
from mmul_gen.templates.base import Case, CaseOutput, Template

if TYPE_CHECKING:
    from mmul_gen.instruction import Instruction

#: The status bit an instruction sets when it rejects an operand.
STATUS_FAULT_BIT = 1

#: A descriptor code outside the encoding the assembler defines.
UNSUPPORTED_DTYPE_CODE = 0x80000008


class MTypeUnsupportedProbe(Template):
    """An out-of-encoding descriptor code must be rejected and change nothing."""

    summary_zh = "编码之外的描述符编码必须被拒绝且不改变任何状态。"
    name = "unsupported_dtype"
    dtypes = PROBE_DTYPE

    def build(
        self, machine: MachineConfig, instruction: Instruction, dtype: DType
    ) -> Sequence[Case]:
        roles = (MRegisterRole("m", machine.nregs(dtype.bits)),)
        # Both physical edges, so the rejection is probed where the register
        # number is lowest and highest rather than only at one end.
        layouts = [
            layout
            for layout in m_register_layouts(machine.num_m_regs, roles)
            if layout.name in {"low", "high"}
        ]
        return [
            Case(number=0, dtype=dtype, layout=RegisterLayout(m=layout))
            for layout in layouts
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
                f"    # case {case.number}: {instruction.name} unsupported datatype "
                "leaves the descriptor unchanged",
                "    csrwi   amestatus, 0",
                f"    li      t0, {case.dtype.name}",
                f"    msettyp m{base}, t0",
                f"    li      t0, {UNSUPPORTED_DTYPE_CODE:#010x}",
                f"    msettyp m{base}, t0",
                "    csrr    t1, amestatus",
                "    andi    t1, t1, 1",
                f"    EXPECT  t1, {STATUS_FAULT_BIT}",
                f"    mgettyp t1, m{base}",
                f"    EXPECT  t1, {case.dtype.name}",
                "",
            ]
        )


__all__ = ["MTypeUnsupportedProbe"]


M_TYPE_UNSUPPORTED_PROBE = MTypeUnsupportedProbe()
