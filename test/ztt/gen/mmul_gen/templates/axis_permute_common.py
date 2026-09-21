#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Shared shape of the row/column control templates.

Every instruction of this family loads a linear ramp ``1..nelem`` into ``m0``,
applies one row/column operation, stores the destination square, and samples the
same five element positions.  Only two things change between the instructions:
the operation's operand lines and the values it is expected to produce.

Each instruction runs a small set of *input cases* -- broadcast from the first or
the last column, shift forward or in reverse, and so on.  Those are cases, not
templates: one template per instruction emits one case per input case per
datatype, which keeps all input cases of a datatype together and lets the driver
keep numbering the cases of the whole file.

The sampled positions are the tuple ``(0, 1, n-1, n, nelem-1)``, duplicates
included: at ``n = 2`` the second and third entries collide and the element is
checked twice.
"""

from __future__ import annotations

DOC_ZH = """\
行/列控制模板的共享形态。

该家族每条指令都把线性斜坡 ``1..nelem`` 加载进 ``m0``，施加一个行/列操作，存储目的方阵，并抽样同样的五个元素位置。指令之间只有两处不同：操作的操作数行和它应产生的值。

每条指令运行一小组*输入用例*——从第一列或最后一列广播、正向或反向平移等。这些是用例，不是模板：每条指令一个模板，按每个 datatype 的每个输入用例发射一个用例，从而保持同一 datatype 的所有输入用例在一起，并让驱动器继续为整个文件编号。

抽样位置是元组 ``(0, 1, n-1, n, nelem-1)``，重复项也保留：在 ``n = 2`` 时第二、三项重合，该元素会被检查两次。
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from mmul_gen.asm import check_dst_element_lines, data_element_lines
from mmul_gen.case_description import description_zh
from mmul_gen.machine import INTEGER, MachineConfig, dtype_stem
from mmul_gen.registers import choose_m_group_base
from mmul_gen.templates.base import Case, CaseOutput, Template, case_payload

if TYPE_CHECKING:
    from mmul_gen.instruction import Instruction
    from mmul_gen.machine import DType


#: The preferred destination base, kept whenever the register file allows it.
PREFERRED_DESTINATION_BASE = 16
#: Shift amount of the forward and reverse shift input cases.
FORWARD_SHIFT = 1
REVERSE_SHIFT = -1


@dataclass(frozen=True)
class AxisPermutePayload:
    """The input case and expected square of one row/column operation case."""

    input_case: str
    expected: tuple[int, ...]


def ramp_source(machine: MachineConfig) -> list[int]:
    """The linear source square ``1..nelem`` every case loads into ``m0``."""

    return list(range(1, machine.nelem + 1))


def checked_positions(machine: MachineConfig) -> tuple[int, ...]:
    """The element positions sampled after the operation, duplicates included."""

    return (0, 1, machine.n - 1, machine.n, machine.nelem - 1)


def source_lines(label: str, values: Sequence[int], element_bits: int) -> list[str]:
    """One labelled input square of ``values``."""

    byte_count = len(values) * element_bits // 8
    return [
        f".balign {byte_count}",
        f"{label}:",
        *data_element_lines(values, element_bits),
    ]


def destination_lines(label: str, element_bits: int, nelem: int) -> list[str]:
    """The touched square, pre-filled so a partial write cannot pass."""

    byte_count = nelem * element_bits // 8
    return [
        f".balign {byte_count}",
        f"{label}:",
        f"    .rept {byte_count}",
        "    .byte 0xa5",
        "    .endr",
    ]


class AxisPermuteTemplate(Template, family_base=True):
    """Shared plumbing of the row/column control instructions."""

    dtypes = INTEGER

    #: Input cases this template runs, in the order it runs them.
    input_cases: tuple[str, ...] = ()

    def expected_values(
        self, machine: MachineConfig, source: Sequence[int], input_case: str
    ) -> list[int]:
        """The expected destination square of one input case."""

        raise NotImplementedError

    def operand_lines(
        self,
        machine: MachineConfig,
        instruction: Instruction,
        input_case: str,
        destination: int,
    ) -> list[str]:
        """The instruction-specific operand setup of one input case."""

        raise NotImplementedError

    def build(
        self,
        machine: MachineConfig,
        instruction: Instruction,
        dtype: DType | None,
    ) -> Sequence[Case]:
        if dtype is None:
            raise ValueError("a row/column operation is always formed from a datatype")
        source = ramp_source(machine)
        return [
            Case(
                number=0,
                dtype=dtype,
                payload=AxisPermutePayload(
                    input_case=input_case,
                    expected=tuple(self.expected_values(machine, source, input_case)),
                ),
                description=description_zh(input_case),
            )
            for input_case in self.input_cases
        ]

    def render(
        self,
        machine: MachineConfig,
        instruction: Instruction,
        case: Case,
        out: CaseOutput,
    ) -> None:
        if case.dtype is None:
            raise ValueError("a row/column operation is always formed from a datatype")
        payload = case_payload(AxisPermutePayload, case)
        element_bits = case.dtype.bits
        destination = choose_m_group_base(
            machine.num_m_regs, element_bits, machine.uds, PREFERRED_DESTINATION_BASE
        )
        prefix = f"case{case.number}_{dtype_stem(case.dtype.name)}_"
        source_label = f"{prefix}source"
        destination_label = f"{prefix}destination"
        out.text.extend(
            [
                f"    # {instruction.name} {case.dtype.name}",
                f"    li      t0, {case.dtype.name}",
                "    msettyp m0, t0",
                f"    msettyp m{destination}, t0",
                f"    la      t1, {source_label}",
                "    mls.rm     m0, t1",
                *self.operand_lines(machine, instruction, payload.input_case, destination),
                f"    la      t2, {destination_label}",
                f"    mss.rm     m{destination}, t2",
            ]
        )
        for index in checked_positions(machine):
            out.text.extend(
                check_dst_element_lines(
                    payload.expected[index], element_bits, index, destination_label
                )
            )
        out.data.extend(source_lines(source_label, ramp_source(machine), element_bits))
        out.data.extend(destination_lines(destination_label, element_bits, machine.nelem))
        out.data.append("")


__all__ = [
    "FORWARD_SHIFT",
    "PREFERRED_DESTINATION_BASE",
    "REVERSE_SHIFT",
    "AxisPermutePayload",
    "AxisPermuteTemplate",
    "checked_positions",
    "destination_lines",
    "ramp_source",
    "source_lines",
]
