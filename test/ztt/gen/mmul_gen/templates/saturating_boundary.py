#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""The saturating one-times-max template."""

from __future__ import annotations

DOC_ZH = """\
饱和“最大值乘一”模板。
"""

from typing import TYPE_CHECKING

from dataclasses import dataclass

from mmul_gen.asm import (
    check_dst_element_lines,
    repeated_square_lines,
)
from mmul_gen.reference import ProductFlags
from mmul_gen.machine import (
    DType,
    MachineConfig,
    SATURATING_INTEGER,
    dtype_stem,
)
from mmul_gen.reference import saturating_edge_product
from mmul_gen.templates.base import (
    Template,
    case_payload,
    paired_cases,
    register,
    two_register_groups_fit,
)

if TYPE_CHECKING:
    from mmul_gen.instruction import Instruction


@dataclass(frozen=True)
class SaturatingPayload:
    """An accumulating product that must saturate at the destination bound."""

    ones: int
    edge: int
    expected: int


class SaturatingBoundary(Template):
    """One-times-max product that must saturate the destination dtype."""

    summary_zh = "必须使目的 datatype 饱和的“最大值乘一”乘积。"
    name = "saturating_boundary"
    dtypes = SATURATING_INTEGER

    def __init__(self, product: ProductFlags) -> None:
        """``product`` is the transposed/negated shape of the instruction's product."""

        self.product = product

    def fits(self, machine: MachineConfig, instruction: Instruction, dtype: DType) -> bool:
        return two_register_groups_fit(machine, dtype)

    def build(self, machine, instruction, dtype):
        expected, edge = saturating_edge_product(
            dtype.name, dtype.bits, machine.n, self.product
        )
        return paired_cases(
            machine,
            dtype,
            SaturatingPayload(ones=1, edge=edge, expected=expected),
        )

    def render(self, machine, instruction, case, out):
        payload = case_payload(SaturatingPayload, case)
        element_bits = case.dtype.bits
        number = case.number
        stem = dtype_stem(case.dtype.name)
        lhs = register("ms1", case.layout)
        rhs = register("ms2", case.layout)
        destination = register("md", case.layout)
        acc = case.layout.acc.base
        prefix = f"case_sat{number}_{stem}_"
        a_square = f"{prefix}a_square"
        b_square = f"{prefix}b_square"

        out.text.extend(
            [
                f"    # saturating case {number}: {instruction.name} {case.dtype.name}",
                f"    li      t0, {case.dtype.name}",
                f"    msettyp m{lhs}, t0",
                f"    msettyp m{rhs}, t0",
                f"    asettyp acc{acc}, t0",
                "    li      t6, 0",
                "    csrw    amexsat, t6",
                "",
                f"    la      t1, {a_square}",
                f"    mls.rm     m{lhs}, t1",
                f"    la      t2, {b_square}",
                f"    mls.rm     m{rhs}, t2",
                f"    mzero.2d.acc acc{acc}",
                f"    {instruction.name} acc{acc}, m{lhs}, m{rhs}",
                f"    mmov.m.a m{destination}, acc{acc}",
                "    la      t3, dst_square",
                f"    mss.rm     m{destination}, t3",
                "    csrr    t4, amexsat",
                "    EXPECT  t4, 1",
            ]
        )
        out.data.extend(repeated_square_lines(a_square, payload.ones, element_bits, machine))
        out.data.extend(repeated_square_lines(b_square, payload.edge, element_bits, machine))
        out.text.extend(check_dst_element_lines(payload.expected, element_bits, 0))
        out.text.extend(check_dst_element_lines(payload.expected, element_bits, machine.nelem - 1))
        out.data.append("")
