#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""The nominal integer log/exp case, shared by every instruction.

One case per datatype: load the source squares an instruction names, apply the
operation in the operand shape it names, store the destination, and check every
element against the value it names.  All of that arrives as constructor
arguments, which is what lets one template cover all twelve instructions.
"""

from __future__ import annotations

DOC_ZH = """\
标称整数 log/exp 用例，由所有指令共享。

每个 datatype 一个用例：加载指令命名的源方阵，按指令命名的操作数形态施加运算，存储目的方阵，并逐元素与指令命名的值比较。这些都作为构造参数传入，这正是让一个模板覆盖全部十二条指令的原因。
"""

from collections.abc import Sequence
from typing import TYPE_CHECKING

from mmul_gen.asm import check_dst_lines, repeated_square_lines
from mmul_gen.machine import INTEGER, MachineConfig
from mmul_gen.templates.base import Case, CaseOutput, Template, domain_index
from mmul_gen.templates.logexp_common import (
    DATA_VALUES,
    LogExpForm,
    DESTINATION_LABEL,
    DESTINATION_REGISTER,
    DESTINATION_SEED_LABEL,
    case_prefix,
    source_registers,
)

if TYPE_CHECKING:
    from mmul_gen.instruction import Instruction
    from mmul_gen.machine import DType


class LogExpNominal(Template):
    """Run the operation on source squares and check the stored result."""

    summary_zh = "在源方阵上执行运算并检查存储结果。"
    name = "nominal"
    dtypes = INTEGER

    def __init__(
        self,
        src1_label: str,
        expected: int,
        form: LogExpForm,
        src2_label: str | None = None,
        scalar: int | None = None,
        initialize_destination: bool = False,
        scalar_dtype_csr: bool = False,
    ) -> None:
        """``src1_label`` is the square read as the first source operand.

        ``expected`` is the value every destination element must hold.
        ``form`` is the operand shape, which decides how many source groups the
        case needs and how the operation is spelled.  ``src2_label`` names the
        second square for the forms that read one; ``scalar`` is the immediate of
        the ``binary_x`` form; ``initialize_destination`` seeds the destination
        from a data square instead of trusting its contents; ``scalar_dtype_csr``
        points ``ame_scalar_dtype`` at the case datatype first.
        """

        self.src1_label = src1_label
        self.expected = expected
        self.form = form
        self.src2_label = src2_label
        self.scalar = scalar
        self.initialize_destination = initialize_destination
        self.scalar_dtype_csr = scalar_dtype_csr

    @property
    def register_groups(self) -> int:
        """M register groups the case needs: destination and sources."""

        return 3 if self.form.reads_second_source else 2

    def operand_lines(
        self,
        instruction: Instruction,
        dest_reg: int,
        src1_reg: int,
        src2_reg: int,
        destination_seed_label: str,
    ) -> list[str]:
        """The setup and the operation itself, in the declared operand shape."""

        lines: list[str] = []
        if self.initialize_destination:
            lines.extend(
                [
                    f"    la      t1, {destination_seed_label}",
                    f"    mls.rm     m{dest_reg}, t1",
                ]
            )
        if self.form is LogExpForm.UNARY:
            lines.append(f"    {instruction.name} m{dest_reg}, m{src1_reg}")
        elif self.form.reads_second_source:
            lines.append(f"    {instruction.name} m{dest_reg}, m{src1_reg}, m{src2_reg}")
        elif self.form is LogExpForm.BINARY_X:
            if self.scalar is None:
                raise ValueError(f"{instruction.name}: the scalar form needs a scalar operand")
            lines.extend(
                [
                    f"    li      t4, {self.scalar}",
                    f"    {instruction.name} m{dest_reg}, t4, m{src1_reg}",
                ]
            )
        else:
            raise ValueError(f"{instruction.name}: unsupported log/exp form {self.form}")
        return lines

    def fits(
        self,
        machine: MachineConfig,
        instruction: Instruction,
        dtype: DType | None = None,
    ) -> bool:
        if dtype is None:
            raise ValueError("a log/exp case is always formed from a datatype")
        return self.register_groups * machine.nregs(dtype.bits) <= machine.num_m_regs

    def build(
        self, machine: MachineConfig, instruction: Instruction, dtype: DType | None
    ) -> Sequence[Case]:
        if dtype is None:
            raise ValueError("a log/exp case is always formed from a datatype")
        return [Case(number=0, dtype=dtype)]

    def render(
        self,
        machine: MachineConfig,
        instruction: Instruction,
        case: Case,
        out: CaseOutput,
    ) -> None:
        if case.dtype is None:
            raise ValueError("a log/exp case is always formed from a datatype")
        dtype = case.dtype
        index = domain_index(machine, dtype, self.dtypes)
        src1_reg, src2_reg = source_registers(machine, dtype.bits)
        prefix = case_prefix("case", index, dtype)
        out.text.extend(
            [
                f"    # case {index}: {instruction.name} {dtype.name}",
                f"    li      t0, {dtype.name}",
                f"    msettyp m{DESTINATION_REGISTER}, t0",
                f"    msettyp m{src1_reg}, t0",
            ]
        )
        if self.form.reads_second_source:
            out.text.append(f"    msettyp m{src2_reg}, t0")
        if self.scalar_dtype_csr:
            out.text.append("    csrw    ame_scalar_dtype, t0")
        out.text.extend(
            [
                "",
                f"    la      t1, {prefix}{self.src1_label}",
                f"    mls.rm     m{src1_reg}, t1",
            ]
        )
        if self.src2_label is not None:
            out.text.extend(
                [
                    f"    la      t2, {prefix}{self.src2_label}",
                    f"    mls.rm     m{src2_reg}, t2",
                ]
            )
        out.text.extend(
            self.operand_lines(instruction,
                DESTINATION_REGISTER,
                src1_reg,
                src2_reg,
                f"{prefix}{DESTINATION_SEED_LABEL}",
            )
        )
        out.text.extend(
            [
                f"    la      t3, {DESTINATION_LABEL}",
                f"    mss.rm     m{DESTINATION_REGISTER}, t3",
                *check_dst_lines(self.expected, dtype.bits, machine=machine),
            ]
        )
        # The seed square is declared even when the case does not read it: the
        # inventory of a case is fixed, and a shorter file would hide a missing
        # initialisation behind a shorter data section.
        labels = {self.src1_label, DESTINATION_SEED_LABEL}
        if self.src2_label is not None:
            labels.add(self.src2_label)
        for label in sorted(labels):
            out.data.extend(
                repeated_square_lines(
                    f"{prefix}{label}", DATA_VALUES[label], dtype.bits, machine
                )
            )
        out.data.append("")


__all__ = ["LogExpNominal"]
