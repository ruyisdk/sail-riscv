#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""The saturating case of an indexed add.

Every index aims at the first row and the destination is seeded with the largest
representable value, so each addition saturates.  The case asserts the status bit
and the clamped destination together.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from mmul_gen.asm import check_dst_element_lines, repeated_square_lines
from mmul_gen.machine import SATURATING_INTEGER, MachineConfig, dtype_stem
from mmul_gen.templates.base import Case, CaseOutput, Template, domain_index
from mmul_gen.templates.matrix_ops_common import (
    byte_index_data_lines,
    destination_lines,
    max_value,
)

if TYPE_CHECKING:
    from mmul_gen.instruction import Instruction
    from mmul_gen.machine import DType


#: The byte-sized descriptor the all-zero index table is read through.
INDEX_DTYPE = "AME_UINT8_DTYPE"


class ScatterSaturating(Template):
    """Saturate an indexed add into an all-maximum destination."""

    name = "scatter_saturating_boundary"
    dtypes = SATURATING_INTEGER

    def fits(
        self,
        machine: MachineConfig,
        instruction: Instruction,
        dtype: DType | None = None,
    ) -> bool:
        if dtype is None:
            raise ValueError("a saturating scatter case is always formed from a datatype")
        return True

    def build(
        self, machine: MachineConfig, instruction: Instruction, dtype: DType | None
    ) -> Sequence[Case]:
        if dtype is None:
            raise ValueError("a saturating scatter case is always formed from a datatype")
        return [Case(number=0, dtype=dtype)]

    def render(
        self,
        machine: MachineConfig,
        instruction: Instruction,
        case: Case,
        out: CaseOutput,
    ) -> None:
        if case.dtype is None:
            raise ValueError("a saturating scatter case is always formed from a datatype")
        dtype = case.dtype
        index = domain_index(machine, dtype, self.dtypes)
        prefix = f"case_sat{index}_{dtype_stem(dtype.name)}_"
        nregs = machine.nregs(dtype.bits)
        destination, addend, table = 0, nregs, machine.num_m_regs - 1
        maximum = max_value(dtype)
        out.text.extend(
            [
                f"    # saturating case {index}: {instruction.name} {dtype.name}",
                f"    li      t0, {dtype.name}",
                f"    msettyp m{destination}, t0",
                f"    msettyp m{addend}, t0",
                f"    li      t1, {INDEX_DTYPE}",
                f"    msettyp m{table}, t1",
                "    li      t6, 0",
                "    csrw    amexsat, t6",
                "",
                f"    la      t1, {prefix}max_square",
                f"    mls.rm     m{destination}, t1",
                f"    la      t2, {prefix}one_square",
                f"    mls.rm     m{addend}, t2",
                f"    la      t3, {prefix}index_zero_square",
                f"    mls.rm     m{table}, t3",
                f"    {instruction.name} m{destination}, m{addend}, m{table}",
                f"    la      t3, {prefix}dst_square",
                f"    mss.rm     m{destination}, t3",
                "    csrr    t5, amexsat",
                "    EXPECT  t5, 1",
                *check_dst_element_lines(
                    maximum, dtype.bits, 0, f"{prefix}dst_square"
                ),
            ]
        )
        out.data.extend(
            repeated_square_lines(f"{prefix}max_square", maximum, dtype.bits, machine)
        )
        out.data.extend(
            repeated_square_lines(f"{prefix}one_square", 1, dtype.bits, machine)
        )
        out.data.extend(
            byte_index_data_lines(f"{prefix}index_zero_square", [0] * machine.nelem)
        )
        out.data.extend(destination_lines(f"{prefix}dst_square", dtype.bits, machine))
        out.data.append("")


__all__ = ["ScatterSaturating"]


SCATTER_SATURATING = ScatterSaturating()
