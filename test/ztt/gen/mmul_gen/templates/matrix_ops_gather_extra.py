#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""The extra-permute case of a column gather.

The index table is a byte image rather than an element-sized square, so the
gather reads it through a UINT8 descriptor whatever the element width is.  That
is the point of the case: the index width and the element width are independent,
and a gather that quietly typed the table as the element descriptor would read
the wrong entry here.
"""

from __future__ import annotations

DOC_ZH = """\
列聚集的额外置换用例。

索引表是字节镜像而不是元素宽度的方阵，因此无论元素宽度如何，聚集都通过 UINT8 描述符读取它。这正是该用例的要点：索引宽度与元素宽度相互独立，若聚集把表悄悄当成元素描述符，就会在这里读到错误的表项。
"""

from collections.abc import Sequence
from typing import TYPE_CHECKING

from mmul_gen.asm import check_dst_element_lines
from mmul_gen.inputs import extra_permute_index_values
from mmul_gen.machine import EXTRA_PERMUTE, MachineConfig, dtype_stem
from mmul_gen.templates.base import Case, CaseOutput, Template, domain_index
from mmul_gen.templates.matrix_ops_common import (
    byte_index_data_lines,
    destination_lines,
    extra_registers,
    source_data_lines,
    values_a,
)

if TYPE_CHECKING:
    from mmul_gen.instruction import Instruction
    from mmul_gen.machine import DType


#: The descriptor the byte-sized index table is read through.
INDEX_DTYPE = "AME_UINT8_DTYPE"


class GatherExtraIndex(Template):
    """Gather through a byte-sized index table on a full-width descriptor."""

    summary_zh = "在满宽描述符上通过字节宽度的索引表聚集。"
    name = "gather_extra_dtype_index"
    dtypes = EXTRA_PERMUTE

    def fits(
        self,
        machine: MachineConfig,
        instruction: Instruction,
        dtype: DType | None = None,
    ) -> bool:
        if dtype is None:
            raise ValueError("an extra gather case is always formed from a datatype")
        return 3 * machine.nregs(dtype.bits) <= machine.num_m_regs

    def build(
        self, machine: MachineConfig, instruction: Instruction, dtype: DType | None
    ) -> Sequence[Case]:
        if dtype is None:
            raise ValueError("an extra gather case is always formed from a datatype")
        return [Case(number=0, dtype=dtype)]

    def render(
        self,
        machine: MachineConfig,
        instruction: Instruction,
        case: Case,
        out: CaseOutput,
    ) -> None:
        if case.dtype is None:
            raise ValueError("an extra gather case is always formed from a datatype")
        dtype = case.dtype
        index = domain_index(machine, dtype, self.dtypes)
        prefix = f"case_extra{index}_{dtype_stem(dtype.name)}_"
        source, second_source, destination, destination_pair, table = extra_registers(
            machine, dtype.bits
        )
        out.text.extend(
            [
                f"    # extra case {index}: {instruction.name} {dtype.name}",
                f"    li      t0, {dtype.name}",
                *[
                    f"    msettyp m{register}, t0"
                    for register in (source, second_source, destination, destination_pair)
                ],
                f"    li      t6, {INDEX_DTYPE}",
                f"    msettyp m{table}, t6",
                "",
                f"    la      t1, {prefix}src_a",
                f"    mls.rm     m{source}, t1",
                f"    la      t2, {prefix}index_square",
                f"    mls.rm     m{table}, t2",
                f"    {instruction.name} m{destination}, m{source}, m{table}",
                f"    la      t3, {prefix}dst_square0",
                f"    mss.rm     m{destination}, t3",
            ]
        )
        values = values_a(machine)
        n = machine.n
        checks = (
            (0, values[1]),
            (n - 1, values[0]),
            (n, values[n + 1]),
        )
        for position, expected in checks:
            out.text.extend(
                check_dst_element_lines(
                    expected, dtype.bits, position, f"{prefix}dst_square0"
                )
            )
        out.data.extend(
            source_data_lines(f"{prefix}src_a", values, dtype.bits, machine)
        )
        out.data.extend(
            byte_index_data_lines(
                f"{prefix}index_square", extra_permute_index_values(n)
            )
        )
        out.data.extend(destination_lines(f"{prefix}dst_square0", dtype.bits, machine))
        out.data.append("")


__all__ = ["INDEX_DTYPE", "GatherExtraIndex"]


GATHER_EXTRA_INDEX = GatherExtraIndex()
