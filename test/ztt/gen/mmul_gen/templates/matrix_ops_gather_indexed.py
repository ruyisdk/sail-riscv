#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""The indexed case of a gather or scatter operation.

The index table is element-sized and carries the axis selector in its top bit,
so the same table drives both axes and both accumulate modes.  A scatter seeds
its destination first -- with ones for the add form, with a value above the ramp
for the max form -- so an untouched element is distinguishable from a written
one.
"""

from __future__ import annotations

DOC_ZH = """\
聚集或散射运算的索引用例。

索引表是元素宽度的，并在最高位携带轴选择位，因此同一张表驱动两个轴和两种累加模式。散射先给目的方阵播种——加法形式播 1，取最大形式播一个高于斜坡的值——因此未触及的元素可与已写入的元素区分。
"""

from collections.abc import Sequence
from typing import TYPE_CHECKING

from mmul_gen.asm import check_dst_element_lines, repeated_square_lines
from mmul_gen.inputs import gather_scatter_index_values
from mmul_gen.machine import INTEGER, MachineConfig, dtype_stem
from mmul_gen.templates.base import Case, CaseOutput, Template, domain_index
from mmul_gen.templates.matrix_ops_common import (
    destination_lines,
    gather_expected,
    scatter_expected,
    source_data_lines,
    values_a,
)

if TYPE_CHECKING:
    from mmul_gen.instruction import Instruction
    from mmul_gen.instructions.matrix_ops.base import MatrixAxis, ScatterAccess
    from mmul_gen.machine import DType


#: Seed of the add form: low enough that every write is visible.
SCATTER_ADD_SEED = 1
#: Seed of the max form: above the ramp, so only a bigger source value wins.
SCATTER_MAX_SEED = 20
#: The first three elements every indexed case samples.
DEFINED_INDICES = (0, 1, 2)
#: Spacing of the two extra sample points.
SAMPLE_STEP = 2


def scatter_seed(access: "ScatterAccess") -> int:
    """The value a scatter seeds its destination with."""

    return SCATTER_MAX_SEED if access.by_max else SCATTER_ADD_SEED


def checked_indices(machine: MachineConfig) -> list[int]:
    """The sampled elements: the start, a spaced pair, and the far boundary."""

    n = machine.n
    return [
        *DEFINED_INDICES,
        n,
        n + SAMPLE_STEP,
        min(7 * n + 6, machine.nelem - 1),
        machine.nelem - 1,
    ]


class GatherScatterIndexed(Template):
    """Move elements through an index table and check the sampled result."""

    summary_zh = "通过索引表搬移元素，并检查抽样结果。"
    name = "gather_indexed_elements"
    dtypes = INTEGER

    def __init__(self, axis: "MatrixAxis", access: "ScatterAccess") -> None:
        """``axis`` is the axis an indexed access walks, ``access`` how it combines.

        A gather reads an element; the accumulating accesses fold it into a
        destination the case seeds first.
        """

        self.axis = axis
        self.access = access

    def fits(
        self,
        machine: MachineConfig,
        instruction: Instruction,
        dtype: DType | None = None,
    ) -> bool:
        if dtype is None:
            raise ValueError("an indexed case is always formed from a datatype")
        # Source, index, and destination each need their own group.
        return 3 * machine.nregs(dtype.bits) <= machine.num_m_regs

    def build(
        self, machine: MachineConfig, instruction: Instruction, dtype: DType | None
    ) -> Sequence[Case]:
        if dtype is None:
            raise ValueError("an indexed case is always formed from a datatype")
        return [Case(number=0, dtype=dtype)]

    def render(
        self,
        machine: MachineConfig,
        instruction: Instruction,
        case: Case,
        out: CaseOutput,
    ) -> None:
        if case.dtype is None:
            raise ValueError("an indexed case is always formed from a datatype")
        dtype = case.dtype
        index = domain_index(machine, dtype, self.dtypes)
        prefix = f"case{index}_{dtype_stem(dtype.name)}_"
        nregs = machine.nregs(dtype.bits)
        source, table, destination = 0, nregs, 2 * nregs
        seed = scatter_seed(self.access)
        out.text.extend(
            [
                f"    # case {index}: {instruction.name} {dtype.name}",
                f"    li      t0, {dtype.name}",
                f"    msettyp m{source}, t0",
                f"    msettyp m{table}, t0",
                f"    msettyp m{destination}, t0",
                "",
                f"    la      t1, {prefix}src_square",
                f"    mls.rm     m{source}, t1",
                f"    la      t2, {prefix}index_square",
                f"    mls.rm     m{table}, t2",
            ]
        )
        if self.access.accumulates:
            seed_label = (
                f"{prefix}init_max_square"
                if seed == SCATTER_MAX_SEED
                else f"{prefix}init_add_square"
            )
            out.text.extend(
                [
                    f"    la      t1, {seed_label}",
                    f"    mls.rm     m{destination}, t1",
                ]
            )
            expected = scatter_expected(machine, self.axis, self.access, dtype, seed)
        else:
            expected = gather_expected(machine, self.axis, dtype)
        out.text.extend(
            [
                f"    {instruction.name} m{destination}, m{source}, m{table}",
                f"    la      t3, {prefix}dst_square",
                f"    mss.rm     m{destination}, t3",
            ]
        )
        for position in checked_indices(machine):
            out.text.extend(
                check_dst_element_lines(
                    expected[position], dtype.bits, position, f"{prefix}dst_square"
                )
            )
        out.data.extend(
            source_data_lines(f"{prefix}src_square", values_a(machine), dtype.bits, machine)
        )
        out.data.extend(
            source_data_lines(
                f"{prefix}index_square",
                gather_scatter_index_values(dtype.bits, machine.n),
                dtype.bits,
                machine,
            )
        )
        for label, value in (
            ("init_add_square", SCATTER_ADD_SEED),
            ("init_max_square", SCATTER_MAX_SEED),
        ):
            out.data.extend(
                repeated_square_lines(f"{prefix}{label}", value, dtype.bits, machine)
            )
        out.data.extend(destination_lines(f"{prefix}dst_square", dtype.bits, machine))
        out.data.append("")


__all__ = [
    "GatherScatterIndexed",
    "SCATTER_ADD_SEED",
    "SCATTER_MAX_SEED",
    "checked_indices",
    "scatter_seed",
]
