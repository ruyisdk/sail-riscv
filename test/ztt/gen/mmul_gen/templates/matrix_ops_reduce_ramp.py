#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""The row-ramp case of a reduce or prefix operation.

The source is the linear ramp ``1..nelem``, which makes every result a closed
form over the active length: each row of the source holds its own row index plus
one, so a whole-row reduce, a column reduce and both prefix shapes all have an
exact expected value without any randomness.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from mmul_gen.asm import check_dst_element_lines
from mmul_gen.machine import INTEGER, MachineConfig, dtype_stem
from mmul_gen.registers import choose_m_group_base
from mmul_gen.templates.base import Case, CaseOutput, Template, domain_index
from mmul_gen.templates.matrix_ops_common import (
    destination_lines,
    reduce_expected,
    source_data_lines,
    values_a,
)

if TYPE_CHECKING:
    from mmul_gen.instruction import Instruction
    from mmul_gen.instructions.matrix_ops.base import MatrixAxis, Reduction
    from mmul_gen.machine import DType


#: Preferred destination base: the ramp cases leave the file's low registers free.
PREFERRED_DESTINATION_BASE = 8


class ReducePrefixRamp(Template):
    """Reduce or prefix a linear ramp and check three sampled elements."""

    name = "reduce_row_ramp"
    dtypes = INTEGER

    def __init__(
        self,
        axis: "MatrixAxis",
        reduction: "Reduction",
        prefix: bool = False,
    ) -> None:
        """``axis`` is the axis each case walks and ``reduction`` how it combines.

        ``prefix`` aggregates only the part of the line up to each element
        instead of the whole line.
        """

        self.axis = axis
        self.reduction = reduction
        self.prefix = prefix

    def fits(
        self,
        machine: MachineConfig,
        instruction: Instruction,
        dtype: DType | None = None,
    ) -> bool:
        if dtype is None:
            raise ValueError("a reduce case is always formed from a datatype")
        return 2 * machine.nregs(dtype.bits) <= machine.num_m_regs

    def build(
        self, machine: MachineConfig, instruction: Instruction, dtype: DType | None
    ) -> Sequence[Case]:
        if dtype is None:
            raise ValueError("a reduce case is always formed from a datatype")
        return [Case(number=0, dtype=dtype)]

    def render(
        self,
        machine: MachineConfig,
        instruction: Instruction,
        case: Case,
        out: CaseOutput,
    ) -> None:
        if case.dtype is None:
            raise ValueError("a reduce case is always formed from a datatype")
        dtype = case.dtype
        index = domain_index(machine, dtype, self.dtypes)
        prefix = f"case{index}_{dtype_stem(dtype.name)}_"
        destination = choose_m_group_base(
            machine.num_m_regs, dtype.bits, machine.uds, PREFERRED_DESTINATION_BASE
        )
        out.text.extend(
            [
                f"    # case {index}: {instruction.name} {dtype.name}",
                f"    li      t0, {dtype.name}",
                "    msettyp m0, t0",
                f"    msettyp m{destination}, t0",
                "",
                f"    la      t1, {prefix}src_square",
                "    mls.rm     m0, t1",
                f"    {instruction.name} m{destination}, m0",
                f"    la      t3, {prefix}dst_square",
                f"    mss.rm     m{destination}, t3",
            ]
        )
        for position, expected in reduce_expected(
            machine, dtype, self.axis, self.reduction, self.prefix
        ):
            out.text.extend(
                check_dst_element_lines(expected, dtype.bits, position, f"{prefix}dst_square")
            )
        out.data.extend(
            source_data_lines(f"{prefix}src_square", values_a(machine), dtype.bits, machine)
        )
        out.data.extend(destination_lines(f"{prefix}dst_square", dtype.bits, machine))
        out.data.append("")


__all__ = ["ReducePrefixRamp"]
