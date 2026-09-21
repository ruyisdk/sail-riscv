#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""The sub-UDS packed source template."""

from __future__ import annotations

DOC_ZH = """\
小于 UDS 的打包源模板。
"""

from dataclasses import dataclass

from mmul_gen.asm import (
    check_dst_lines,
    repeated_square_lines,
)
from mmul_gen.reference import ProductFlags
from mmul_gen.machine import (
    PACKED_INTEGER,
    dtype_stem,
)
from mmul_gen.reference import (
    PACKED_LHS_VALUE,
    PACKED_RHS_VALUE,
    packed_compute_dtype,
    packed_product,
)
from mmul_gen.templates.base import (
    Template,
    case_payload,
    flatten,
    paired_cases,
    register,
)


@dataclass(frozen=True)
class PackedPayload:
    """A source stored narrower than one UDS, widened at writeback."""

    lhs: int
    rhs: int
    dest_dtype: str
    expected: tuple[int, ...]


class PackedSmall(Template):
    """Sub-UDS packed integer source widened into a whole-register product."""

    summary_zh = "小于 UDS 的打包整数源，扩展为整寄存器乘积。"
    name = "packed_small"
    dtypes = PACKED_INTEGER

    def __init__(self, product: ProductFlags) -> None:
        """``product`` is the transposed/negated shape of the instruction's product."""

        self.product = product

    def build(self, machine, instruction, dtype):
        expected = packed_product(
            dtype.name, dtype.bits, machine.uds, machine.n, self.product
        )
        return paired_cases(
            machine,
            dtype,
            PackedPayload(
                lhs=PACKED_LHS_VALUE,
                rhs=PACKED_RHS_VALUE,
                dest_dtype=packed_compute_dtype(dtype.name, machine.uds),
                expected=flatten(expected),
            ),
            destination_bits=machine.uds,
        )

    def render(self, machine, instruction, case, out):
        payload = case_payload(PackedPayload, case)
        element_bits = case.dtype.bits
        if element_bits >= machine.uds:
            raise ValueError("packed matrix case requires a storage-only source")

        number = case.number
        destination_bits = machine.uds
        stem = dtype_stem(case.dtype.name)
        lhs = register("ms1", case.layout)
        rhs = register("ms2", case.layout)
        destination = register("md", case.layout)
        acc = case.layout.acc.base
        prefix = f"packed{number}_{stem}_"
        lhs_label = f"{prefix}lhs"
        rhs_label = f"{prefix}rhs"
        dst_label = f"{prefix}dst"

        out.text.extend(
            [
                f"    # packed case {number}: {instruction.name} {case.dtype.name}"
                f" -> {payload.dest_dtype}",
                f"    li      t0, {case.dtype.name}",
                f"    msettyp m{lhs}, t0",
                f"    msettyp m{rhs}, t0",
                f"    li      t0, {payload.dest_dtype}",
                f"    asettyp acc{acc}, t0",
                "",
                f"    la      t1, {lhs_label}",
                f"    mls.rm     m{lhs}, t1",
                f"    la      t2, {rhs_label}",
                f"    mls.rm     m{rhs}, t2",
                f"    mzero.2d.acc acc{acc}",
                f"    {instruction.name} acc{acc}, m{lhs}, m{rhs}",
                f"    msettyp m{destination}, t0",
                f"    mmov.m.a m{destination}, acc{acc}",
                f"    la      t3, {dst_label}",
                f"    mss.rm     m{destination}, t3",
            ]
        )
        out.text.extend(
            check_dst_lines(payload.expected[0], destination_bits, machine=machine, label=dst_label)
        )

        out.data.extend(repeated_square_lines(lhs_label, payload.lhs, element_bits, machine))
        out.data.extend(repeated_square_lines(rhs_label, payload.rhs, element_bits, machine))
        out.data.extend(repeated_square_lines(dst_label, 0, destination_bits, machine))
        out.data.append("")
