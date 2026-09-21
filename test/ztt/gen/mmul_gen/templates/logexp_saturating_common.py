#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Shared shape of the saturating log/exp cases.

A saturating case checks two independent things: that the result clamps to the
largest representable value, *and* that the operation reported the saturation
through ``amexsat``.  Both are asserted, so a wrong result and a missing status
bit cannot mask each other.

The group is its own template because its datatype domain is the saturating
descriptors rather than the plain ones, and because these cases are numbered
separately -- ``# saturating case 0`` starts again for the saturating
group and again for the 128-bit group.
"""

from __future__ import annotations

DOC_ZH = """\
饱和 log/exp 用例的共享形态。

饱和用例检查两件独立的事情：结果钳到最大可表示值，*并且*运算通过 ``amexsat`` 报告了饱和。两者都被断言，因此错误结果与缺失状态位不会互相掩盖。

该组有自己的模板，因为它的 datatype 域是饱和描述符而不是普通描述符，也因为这些用例单独编号——``# saturating case 0`` 在饱和组重新开始，在 128 位组再重新开始。
"""

from collections.abc import Sequence
from typing import TYPE_CHECKING

from mmul_gen.asm import check_dst_lines, repeated_square_lines
from mmul_gen.machine import SATURATING_INTEGER, MachineConfig
from mmul_gen.templates.base import Case, CaseOutput, Template, domain_index
from mmul_gen.templates.logexp_common import (
    DESTINATION_LABEL,
    LogExpForm,
    DESTINATION_REGISTER,
    case_prefix,
    saturating_max,
    source_registers,
)

if TYPE_CHECKING:
    from mmul_gen.instruction import Instruction
    from mmul_gen.machine import DType


class SaturatingLogExpTemplate(Template, family_base=True):
    """Clamp an unrepresentable result and report that it saturated."""

    dtypes = SATURATING_INTEGER

    def __init__(self, form: LogExpForm, initialize_destination: bool = False) -> None:
        """``form`` is the instruction's operand shape and decides its sources.

        ``initialize_destination`` says whether the case seeds the destination
        from a data square, which is what makes it need three register groups.
        """

        self.form = form
        self.initialize_destination = initialize_destination

    def saturating_operand_lines(
        self,
        machine: MachineConfig,
        instruction: Instruction,
        dtype: DType,
        prefix: str,
    ) -> list[str]:
        """Load what the operation reads and apply it."""

        raise NotImplementedError

    def saturating_data_lines(
        self,
        machine: MachineConfig,
        instruction: Instruction,
        dtype: DType,
        prefix: str,
    ) -> list[str]:
        """The data squares this group's cases read."""

        raise NotImplementedError

    def fits(
        self,
        machine: MachineConfig,
        instruction: Instruction,
        dtype: DType | None = None,
    ) -> bool:
        if dtype is None:
            raise ValueError("a saturating log/exp case is always formed from a datatype")
        # Only the accumulate form keeps a destination and two sources live at
        # once; the in-place form works in one group whatever the width.
        if self.initialize_destination:
            return 3 * machine.nregs(dtype.bits) <= machine.num_m_regs
        return True

    def build(
        self, machine: MachineConfig, instruction: Instruction, dtype: DType | None
    ) -> Sequence[Case]:
        if dtype is None:
            raise ValueError("a saturating log/exp case is always formed from a datatype")
        return [Case(number=0, dtype=dtype)]

    def render(
        self,
        machine: MachineConfig,
        instruction: Instruction,
        case: Case,
        out: CaseOutput,
    ) -> None:
        if case.dtype is None:
            raise ValueError("a saturating log/exp case is always formed from a datatype")
        dtype = case.dtype
        index = domain_index(machine, dtype, self.dtypes)
        prefix = case_prefix("case_sat", index, dtype)
        out.text.extend(
            [
                f"    # saturating case {index}: {instruction.name} {dtype.name}",
                f"    li      t0, {dtype.name}",
                f"    msettyp m{DESTINATION_REGISTER}, t0",
            ]
        )
        if self.form.reads_second_source:
            src1_reg, src2_reg = source_registers(machine, dtype.bits)
            out.text.extend([f"    msettyp m{src1_reg}, t0", f"    msettyp m{src2_reg}, t0"])
        out.text.extend(
            [
                "    li      t6, 0",
                "    csrw    amexsat, t6",
                "",
                *self.saturating_operand_lines(machine, instruction, dtype, prefix),
                f"    la      t3, {DESTINATION_LABEL}",
                f"    mss.rm     m{DESTINATION_REGISTER}, t3",
                "    csrr    t5, amexsat",
                "    EXPECT  t5, 1",
                *check_dst_lines(saturating_max(dtype), dtype.bits, machine=machine),
            ]
        )
        out.data.extend(self.saturating_data_lines(machine, instruction, dtype, prefix))
        out.data.append("")


def clamped_square(machine: MachineConfig, dtype: DType, prefix: str, label: str) -> list[str]:
    """A data square holding the largest representable value."""

    return repeated_square_lines(
        f"{prefix}{label}", saturating_max(dtype), dtype.bits, machine
    )


__all__ = ["SaturatingLogExpTemplate", "clamped_square"]
