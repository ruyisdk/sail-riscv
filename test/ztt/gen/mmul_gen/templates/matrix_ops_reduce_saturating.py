#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""The saturating case of a reduce or prefix operation.

Reducing a square that already holds the largest representable value cannot
produce a representable result, so the operation must clamp *and* report the
saturation.  Both are asserted: a wrong result and a missing status bit cannot
mask each other.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from mmul_gen.asm import check_dst_element_lines, repeated_square_lines
from mmul_gen.machine import SATURATING_INTEGER, MachineConfig, dtype_stem
from mmul_gen.templates.base import Case, CaseOutput, Template, domain_index
from mmul_gen.templates.matrix_ops_common import destination_lines, max_value

if TYPE_CHECKING:
    from mmul_gen.instruction import Instruction
    from mmul_gen.machine import DType


class ReducePrefixSaturating(Template):
    """Clamp a reduce of the all-maximum square and report saturation."""

    name = "reduce_saturating_boundary"
    dtypes = SATURATING_INTEGER

    def fits(
        self,
        machine: MachineConfig,
        instruction: Instruction,
        dtype: DType | None = None,
    ) -> bool:
        if dtype is None:
            raise ValueError("a saturating reduce case is always formed from a datatype")
        # The operation is in place: one group for the source and destination.
        return machine.nregs(dtype.bits) <= machine.num_m_regs

    def build(
        self, machine: MachineConfig, instruction: Instruction, dtype: DType | None
    ) -> Sequence[Case]:
        if dtype is None:
            raise ValueError("a saturating reduce case is always formed from a datatype")
        return [Case(number=0, dtype=dtype)]

    def render(
        self,
        machine: MachineConfig,
        instruction: Instruction,
        case: Case,
        out: CaseOutput,
    ) -> None:
        if case.dtype is None:
            raise ValueError("a saturating reduce case is always formed from a datatype")
        dtype = case.dtype
        index = domain_index(machine, dtype, self.dtypes)
        prefix = f"case_sat{index}_{dtype_stem(dtype.name)}_"
        maximum = max_value(dtype)
        out.text.extend(
            [
                f"    # saturating case {index}: {instruction.name} {dtype.name}",
                f"    li      t0, {dtype.name}",
                "    msettyp m0, t0",
                "    li      t6, 0",
                "    csrw    amexsat, t6",
                "",
                f"    la      t1, {prefix}max_square",
                "    mls.rm     m0, t1",
                f"    {instruction.name} m0, m0",
                f"    la      t3, {prefix}dst_square",
                "    mss.rm     m0, t3",
                "    csrr    t5, amexsat",
                "    EXPECT  t5, 1",
                *check_dst_element_lines(maximum, dtype.bits, 0, f"{prefix}dst_square"),
                *check_dst_element_lines(
                    maximum, dtype.bits, machine.nelem - 1, f"{prefix}dst_square"
                ),
            ]
        )
        out.data.extend(
            repeated_square_lines(f"{prefix}max_square", maximum, dtype.bits, machine)
        )
        out.data.extend(destination_lines(f"{prefix}dst_square", dtype.bits, machine))
        out.data.append("")


__all__ = ["ReducePrefixSaturating"]


REDUCE_SATURATING = ReducePrefixSaturating()
