#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Shared shape of the accumulator utility templates.

Every case zeroes one register file and copies the result into the other one, so
a single all-zero image check proves three things at once: the zeroing wrote the
whole operand, the copy moved the whole operand, and nothing outside the operand
was disturbed.  Only the operation differs between the four instructions, so that
part is a hook and the plumbing lives here.

Unlike the matrix-product cases, a utility touches exactly one accumulator per
case, so these templates cycle *every* legal accumulator rather than the
low/boundary/high representative subset: skipping a middle accumulator would
leave it untested.

The ``# input:`` label is emitted *after* the register layout comments, the
other way round from the type-register family.  That is why these cases carry no
``description`` and the label is emitted from ``render`` instead: the driver
writes the layout comments first and then the template's text, and the label is
the template's Chinese name.
"""

from __future__ import annotations

DOC_ZH = """\
累加器工具模板的共享形态。

每个用例把一个寄存器文件清零并把结果拷贝到另一个，因此一次全零镜像检查同时证明三件事：清零写满了整个操作数、拷贝搬移了整个操作数、操作数之外没有被扰动。四条指令之间只有操作不同，因此操作是钩子，管线逻辑放在这里。

与矩阵乘用例不同，工具每条用例只触及一个累加器，因此这些模板轮转*每一个*合法累加器，而不是 low/boundary/high 代表性子集：跳过中间的累加器会让它得不到测试。

``# input:`` 标签发在寄存器布局注释*之后*，与 type-register 家族相反。这就是这些用例不携带 ``description``、而由 ``render`` 发射标签的原因：驱动器先写布局注释，再写模板的文本，标签取模板的中文名。
"""

from collections.abc import Sequence
from typing import TYPE_CHECKING, ClassVar

from mmul_gen.asm import load_byte_lines
from mmul_gen.case_description import description_zh
from mmul_gen.machine import INTEGER, MachineConfig, dtype_stem
from mmul_gen.registers import (
    MRegisterRole,
    RegisterLayout,
    m_register_layouts,
    paired_layouts,
)
from mmul_gen.templates.base import Case, CaseOutput, Template

if TYPE_CHECKING:
    from mmul_gen.instruction import Instruction
    from mmul_gen.machine import DType


#: Fill byte of the destination square the utility has to overwrite.
UNTOUCHED_BYTE = 0xA5


def require_accumulator(layout: RegisterLayout) -> int:
    """Accumulator number of a layout that must carry one."""

    if layout.acc is None:
        raise ValueError("this accumulator utility instruction needs an accumulator layout")
    return layout.acc.base


def zero_acc_then_copy_out(out_reg: int, acc_reg: int, destination_label: str) -> list[str]:
    """Zero an accumulator, read it back into an M register, store that square."""

    return [
        f"    msettyp m{out_reg}, t0",
        f"    asettyp acc{acc_reg}, t0",
        f"    mzero.2d.acc acc{acc_reg}",
        f"    mmov.m.a m{out_reg}, acc{acc_reg}",
        f"    la      t1, {destination_label}",
        f"    mss.rm     m{out_reg}, t1",
    ]


def zero_m_then_copy_out(out_reg: int, destination_label: str) -> list[str]:
    """Zero an M register and store that square."""

    return [
        f"    msettyp m{out_reg}, t0",
        f"    mzero.2d.m m{out_reg}",
        f"    la      t1, {destination_label}",
        f"    mss.rm     m{out_reg}, t1",
    ]


def m_to_acc_then_copy_out(
    source_reg: int, out_reg: int, acc_reg: int, destination_label: str
) -> list[str]:
    """Zero an M register, move it into an accumulator, and read it back out."""

    return [
        f"    msettyp m{source_reg}, t0",
        f"    asettyp acc{acc_reg}, t0",
        f"    mzero.2d.m m{source_reg}",
        f"    mmov.a.m acc{acc_reg}, m{source_reg}",
        f"    mmov.m.a m{out_reg}, acc{acc_reg}",
        f"    la      t1, {destination_label}",
        f"    mss.rm     m{out_reg}, t1",
    ]


class AccumulatorUtilityTemplate(Template, family_base=True):
    """One accumulator utility instruction, parameterised by its operation."""

    dtypes = INTEGER

    #: Whether the instruction addresses an accumulator operand.
    uses_accumulator: ClassVar[bool] = True

    def m_register_roles(
        self, machine: MachineConfig, dtype: DType
    ) -> tuple[MRegisterRole, ...]:
        """M-register operands this instruction addresses."""

        return (MRegisterRole("md", machine.nregs(dtype.bits)),)

    def layouts(
        self, machine: MachineConfig, dtype: DType
    ) -> tuple[RegisterLayout, ...]:
        roles = self.m_register_roles(machine, dtype)
        if not self.uses_accumulator:
            return tuple(
                RegisterLayout(m=layout)
                for layout in m_register_layouts(machine.num_m_regs, roles)
            )
        return paired_layouts(
            machine.num_m_regs,
            machine.num_acc_regs,
            roles,
            exhaustive_accumulators=True,
        )

    def build(
        self, machine: MachineConfig, instruction: Instruction, dtype: DType
    ) -> Sequence[Case]:
        return [
            Case(number=0, dtype=dtype, layout=layout)
            for layout in self.layouts(machine, dtype)
        ]

    def operation_lines(
        self,
        instruction: Instruction,
        layout: RegisterLayout,
        destination_label: str,
    ) -> list[str]:
        """The instruction-specific part of one case."""

        raise NotImplementedError

    def render(
        self,
        machine: MachineConfig,
        instruction: Instruction,
        case: Case,
        out: CaseOutput,
    ) -> None:
        if case.dtype is None or case.layout is None:
            raise ValueError("an accumulator case needs a datatype and a layout")
        element_bits = case.dtype.bits
        square_bytes = machine.nelem * element_bits // 8
        destination_label = f"case{case.number}_{dtype_stem(case.dtype.name)}_dst_square"
        acc_reg = case.layout.acc.base if case.layout.acc is not None else None
        if self.uses_accumulator and acc_reg is None:
            raise ValueError(f"{instruction.name} needs an accumulator layout")

        out.text.extend(
            [
                f"    # input: {description_zh(self.name)}",
                f"    # case {case.number}: {instruction.name} {case.dtype.name}",
                f"    li      t0, {case.dtype.name}",
                *self.operation_lines(instruction, case.layout, destination_label),
                "",
                f"    la      t2, {destination_label}",
                "    lbu     t3, 0(t2)",
                "    EXPECT  t3, 0",
                *load_byte_lines("t3", "t2", square_bytes - 1),
                "    EXPECT  t3, 0",
                "",
            ]
        )
        out.data.extend(
            [
                f".balign {square_bytes}",
                f"{destination_label}:",
                f"    .rept {square_bytes}",
                f"    .byte 0x{UNTOUCHED_BYTE:02x}",
                "    .endr",
                "",
            ]
        )


__all__ = [
    "UNTOUCHED_BYTE",
    "require_accumulator",
    "AccumulatorUtilityTemplate",
    "m_to_acc_then_copy_out",
    "zero_acc_then_copy_out",
    "zero_m_then_copy_out",
]
