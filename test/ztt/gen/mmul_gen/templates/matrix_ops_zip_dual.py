#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""The dual-source case of a zip or unzip operation.

Two ramps are loaded, the operation merges or splits them, and both halves of the
result are stored and checked.  The two ramps start far enough apart that the
value of an element says which source square it came from, which is what makes a
wrongly interleaved result visible.
"""

from __future__ import annotations

DOC_ZH = """\
zip 或 unzip 运算的双源用例。

加载两个斜坡，运算合并或拆分它们，结果的两半都被存储并检查。两个斜坡起始值相距足够远，使某个元素的值能说明它来自哪个源方阵，这正是让交错错误的结果可见的原因。
"""

from collections.abc import Sequence
from typing import TYPE_CHECKING

from mmul_gen.asm import check_dst_element_lines
from mmul_gen.machine import INTEGER, MachineConfig, dtype_stem
from mmul_gen.templates.base import Case, CaseOutput, Template, domain_index
from mmul_gen.templates.matrix_ops_common import (
    destination_lines,
    source_data_lines,
    values_a,
    values_b,
)

if TYPE_CHECKING:
    from mmul_gen.instruction import Instruction
    from mmul_gen.instructions.matrix_ops.base import MatrixAxis
    from mmul_gen.machine import DType


def zip_results(
    machine: MachineConfig, axis: "MatrixAxis", unzip: bool
) -> tuple[list[int], list[int]]:
    """The two expected halves of one zip or unzip case."""

    n = machine.n
    half = n // 2
    first = values_a(machine)
    second = values_b(machine)
    halves = ([0] * machine.nelem, [0] * machine.nelem)
    for row in range(n):
        for col in range(n):
            position = row * n + col
            coordinate = axis.varying(row, col)
            if unzip:
                source_coordinate = coordinate - half if coordinate >= half else coordinate
                source = first if coordinate < half else second
                low = axis.result_index(n, row, col, 2 * source_coordinate)
                high = axis.result_index(n, row, col, 2 * source_coordinate + 1)
            else:
                source_coordinate = coordinate // 2
                source = first if coordinate % 2 == 0 else second
                low = axis.result_index(n, row, col, source_coordinate)
                high = axis.result_index(n, row, col, half + source_coordinate)
            halves[0][position] = source[low]
            halves[1][position] = source[high]
    return halves


def checked_indices(machine: MachineConfig) -> tuple[int, ...]:
    """The sampled elements of each half: start, second, and the far boundary."""

    n = machine.n
    return (0, 1, n - 1, n, machine.nelem - 1)


class ZipDualSource(Template):
    """Merge or split two ramps and check both halves of the result."""

    summary_zh = "合并或拆分两个斜坡，并检查结果的两半。"
    name = "zip_dual_source_ramp"
    dtypes = INTEGER

    def __init__(self, axis: "MatrixAxis", unzip: bool = False) -> None:
        """``axis`` is the axis the stream runs along; ``unzip`` splits instead of merges."""

        self.axis = axis
        self.unzip = unzip
    #: The extra-permute variant only differs in its label prefix.
    extra: bool = False

    def fits(
        self,
        machine: MachineConfig,
        instruction: Instruction,
        dtype: DType | None = None,
    ) -> bool:
        if dtype is None:
            raise ValueError("a zip case is always formed from a datatype")
        # The extra variant needs three disjoint groups; the plain dual-source
        # case writes its result back into the two source groups.
        if self.extra:
            return 3 * machine.nregs(dtype.bits) <= machine.num_m_regs
        return True

    def build(
        self, machine: MachineConfig, instruction: Instruction, dtype: DType | None
    ) -> Sequence[Case]:
        if dtype is None:
            raise ValueError("a zip case is always formed from a datatype")
        return [Case(number=0, dtype=dtype)]

    def render(
        self,
        machine: MachineConfig,
        instruction: Instruction,
        case: Case,
        out: CaseOutput,
    ) -> None:
        if case.dtype is None:
            raise ValueError("a zip case is always formed from a datatype")
        dtype = case.dtype
        index = domain_index(machine, dtype, self.dtypes)
        kind = "caseextra" if self.extra else "case"
        prefix = f"{kind}{index}_{dtype_stem(dtype.name)}_"
        nregs = machine.nregs(dtype.bits)
        source_a, source_b = 0, nregs
        out.text.extend(
            [
                f"    # case {index}: {instruction.name} {dtype.name}",
                f"    li      t0, {dtype.name}",
                f"    msettyp m{source_a}, t0",
                f"    msettyp m{source_b}, t0",
                "",
                f"    la      t1, {prefix}src_a",
                f"    mls.rm     m{source_a}, t1",
                f"    la      t2, {prefix}src_b",
                f"    mls.rm     m{source_b}, t2",
                f"    {instruction.name} m{source_a}, m{source_b}",
                f"    la      t3, {prefix}dst_square0",
                f"    mss.rm     m{source_a}, t3",
                f"    la      t3, {prefix}dst_square1",
                f"    mss.rm     m{source_b}, t3",
            ]
        )
        first, second = zip_results(machine, self.axis, self.unzip)
        for label, values in (("dst_square0", first), ("dst_square1", second)):
            for position in checked_indices(machine):
                out.text.extend(
                    check_dst_element_lines(
                        values[position], dtype.bits, position, f"{prefix}{label}"
                    )
                )
        out.data.extend(
            source_data_lines(f"{prefix}src_a", values_a(machine), dtype.bits, machine)
        )
        out.data.extend(
            source_data_lines(f"{prefix}src_b", values_b(machine), dtype.bits, machine)
        )
        out.data.extend(destination_lines(f"{prefix}dst_square0", dtype.bits, machine))
        out.data.extend(destination_lines(f"{prefix}dst_square1", dtype.bits, machine))
        out.data.append("")


__all__ = ["ZipDualSource", "checked_indices", "zip_results"]
