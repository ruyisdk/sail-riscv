#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""The position-dependent small-matrix product template."""

from __future__ import annotations

from dataclasses import dataclass

from mmul_gen.asm import (
    check_dst_element_lines,
    data_element_lines,
)
from mmul_gen.inputs import small_matrix_inputs
from mmul_gen.reference import ProductFlags
from mmul_gen.machine import (
    INTEGER,
    dtype_stem,
)
from mmul_gen.reference import small_matrix_product
from mmul_gen.templates.base import (
    Template,
    case_payload,
    flatten,
    paired_cases,
    register,
)


@dataclass(frozen=True)
class MatrixSmallPayload:
    """The position-dependent small-matrix stimulus."""

    a: tuple[int, ...]
    b: tuple[int, ...]
    expected: tuple[int, ...]


class MatrixSmall(Template):
    """Position-dependent small-matrix product with transposed/negated variants."""

    name = "matrix_small"
    dtypes = INTEGER

    def __init__(self, product: ProductFlags) -> None:
        """``product`` is the transposed/negated shape of the instruction's product."""

        self.product = product

    def build(self, machine, instruction, dtype):
        a_values, b_values = small_matrix_inputs(machine.n)
        expected = small_matrix_product(
            dtype.name, dtype.bits, machine.n, self.product
        )
        return paired_cases(
            machine,
            dtype,
            MatrixSmallPayload(a=flatten(a_values), b=flatten(b_values), expected=flatten(expected)),
        )

    def render(self, machine, instruction, case, out):
        payload = case_payload(MatrixSmallPayload, case)
        element_bits = case.dtype.bits
        if element_bits not in {8, 16, 32, 64}:
            raise ValueError(f"unsupported 2D matmul variant element width: {element_bits}")

        number = case.number
        n = machine.n
        elem_bytes = element_bits // 8
        square_bytes = machine.nelem * elem_bytes
        lhs = register("ms1", case.layout)
        rhs = register("ms2", case.layout)
        destination = register("md", case.layout)
        acc = case.layout.acc.base
        stem = dtype_stem(case.dtype.name)
        a_square = f"case{number}_{stem}_a_square"
        b_square = f"case{number}_{stem}_b_square"
        checks = (0, 1, n, min(3 * n + 4, machine.nelem - 1), machine.nelem - 1)

        out.text.extend(
            [
                f"    # case {number}: {instruction.name} {case.dtype.name}",
                f"    li      t0, {case.dtype.name}",
                f"    msettyp m{lhs}, t0",
                f"    msettyp m{rhs}, t0",
                f"    asettyp acc{acc}, t0",
                "",
            ]
        )
        out.text.extend(
            [
                f"    la      t1, {a_square}",
                f"    mls.rm     m{lhs}, t1",
                f"    mzero.2d.acc acc{acc}",
                f"    la      t2, {b_square}",
                f"    mls.rm     m{rhs}, t2",
                f"    {instruction.name} acc{acc}, m{lhs}, m{rhs}",
                f"    mmov.m.a m{destination}, acc{acc}",
                "    la      t3, dst_square",
                f"    mss.rm     m{destination}, t3",
            ]
        )
        for element_index in checks:
            out.text.extend(
                check_dst_element_lines(payload.expected[element_index], element_bits, element_index)
            )

        for label, values in ((a_square, payload.a), (b_square, payload.b)):
            out.data.extend(
                [
                    f".balign {square_bytes}",
                    f"{label}:",
                    *data_element_lines(list(values), element_bits),
                ]
            )
        out.data.append("")
