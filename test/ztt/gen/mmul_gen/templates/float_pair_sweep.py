#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""The exactly-representable float product and overflow sweep template."""

from __future__ import annotations

DOC_ZH = """\
可精确表示的浮点乘积与上溢扫描模板。
"""

from dataclasses import dataclass

from mmul_gen.asm import (
    check_dst_lines,
    data_directive,
    hex_value,
    repeated_square_lines,
)
from mmul_gen.float_formats import softfloat_product_expected
from mmul_gen.inputs import (
    FFLAGS_OF_NX,
    FloatOverflowBoundary,
    ROUNDING_MODE_DTYPES,
    SOFTFLOAT_ONE,
    float_overflow_boundaries,
    softfloat_two,
)
from mmul_gen.reference import ProductFlags
from mmul_gen.machine import (
    SOFTFLOAT,
    dtype_stem,
)
from mmul_gen.templates.base import (
    Template,
    case_payload,
    paired_cases,
    register,
)


@dataclass(frozen=True)
class FloatNominalPayload:
    """Exactly representable all-ones float product."""

    one: int
    expected: int


@dataclass(frozen=True)
class FloatOverflowPayload:
    """Largest-finite times two, swept over every rounding mode and sign."""

    two: int
    boundaries: tuple[FloatOverflowBoundary, ...]


class FloatPairSweep(Template):
    """Exactly representable float product plus a sign x rounding overflow sweep."""

    summary_zh = "可精确表示的浮点乘积，外加符号 × 舍入的上溢扫描。"
    name = "float_pair_sweep"
    dtypes = SOFTFLOAT

    def __init__(self, product: ProductFlags) -> None:
        """``product`` is the transposed/negated shape of the instruction's product."""

        self.product = product

    def build(self, machine, instruction, dtype):
        dtype_name = dtype.name
        negated = self.product.subtract
        nominal = paired_cases(
            machine,
            dtype,
            FloatNominalPayload(
                one=SOFTFLOAT_ONE[dtype_name],
                expected=softfloat_product_expected(dtype_name, machine.n, negated=negated),
            ),
        )
        overflow = paired_cases(
            machine,
            dtype,
            FloatOverflowPayload(
                two=softfloat_two(dtype_name),
                boundaries=float_overflow_boundaries(
                    dtype_name, dtype.bits, negated_product=negated
                ),
            ),
        )
        return [*nominal, *overflow]

    def render(self, machine, instruction, case, out):
        if isinstance(case.payload, FloatNominalPayload):
            self._render_nominal(machine, instruction, case, out)
        elif isinstance(case.payload, FloatOverflowPayload):
            self._render_overflow(machine, instruction, case, out)
        else:
            raise TypeError(f"case {case.number}: unexpected float payload type")

    def _render_nominal(self, machine, instruction, case, out):
        payload = case_payload(FloatNominalPayload, case)
        element_bits = case.dtype.bits
        number = case.number
        directive = data_directive(element_bits)
        square_bytes = machine.nelem * element_bits // 8
        stem = dtype_stem(case.dtype.name)
        lhs = register("ms1", case.layout)
        rhs = register("ms2", case.layout)
        destination = register("md", case.layout)
        acc = case.layout.acc.base
        a_square = f"case{number}_{stem}_a_square"
        b_square = f"case{number}_{stem}_b_square"

        out.text.extend(
            [
                f"    # case {number}: {instruction.name} {case.dtype.name}",
                f"    li      t0, {case.dtype.name}",
                f"    msettyp m{lhs}, t0",
                f"    msettyp m{rhs}, t0",
                f"    asettyp acc{acc}, t0",
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
            ]
        )
        out.text.extend(check_dst_lines(payload.expected, element_bits, machine=machine))

        for label in (a_square, b_square):
            out.data.extend(
                [
                    f".balign {square_bytes}",
                    f"{label}:",
                    f"    .rept {machine.nelem}",
                    f"    {directive} {hex_value(payload.one, element_bits)}",
                    "    .endr",
                ]
            )
        out.data.append("")

    def _render_overflow(self, machine, instruction, case, out):
        payload = case_payload(FloatOverflowPayload, case)
        element_bits = case.dtype.bits
        number = case.number
        stem = dtype_stem(case.dtype.name)
        lhs = register("ms1", case.layout)
        rhs = register("ms2", case.layout)
        destination = register("md", case.layout)
        acc = case.layout.acc.base

        for boundary_id, boundary in enumerate(payload.boundaries):
            sign = "negative" if boundary.output_negative else "positive"
            for mode, expected in boundary.per_mode:
                prefix = f"boundary{number}_{boundary_id}_{stem}_{mode}_{sign}_"
                lhs_label = f"{prefix}lhs_square"
                rhs_label = f"{prefix}rhs_square"
                dst_label = f"{prefix}dst_square"
                out.text.extend(
                    [
                        f"    # {instruction.name} {case.dtype.name}: {sign} overflow {mode}",
                        "    ame.release",
                        "    li      t0, 0",
                        "    ame.acquire t1, t0",
                        "    EXPECT  t1, 1",
                        f"    li      t0, {case.dtype.name} | {ROUNDING_MODE_DTYPES[mode]}",
                        f"    msettyp m{lhs}, t0",
                        f"    msettyp m{rhs}, t0",
                        f"    asettyp acc{acc}, t0",
                        f"    la      t1, {lhs_label}",
                        f"    mls.rm     m{lhs}, t1",
                        f"    la      t2, {rhs_label}",
                        f"    mls.rm     m{rhs}, t2",
                        f"    mzero.2d.acc acc{acc}",
                        f"    {instruction.name} acc{acc}, m{lhs}, m{rhs}",
                        f"    mmov.m.a m{destination}, acc{acc}",
                        "    csrr    t5, amefflags",
                        f"    EXPECT  t5, {FFLAGS_OF_NX}",
                        f"    la      t3, {dst_label}",
                        f"    mss.rm     m{destination}, t3",
                    ]
                )
                out.data.extend(
                    repeated_square_lines(lhs_label, boundary.source_value, element_bits, machine)
                )
                out.data.extend(repeated_square_lines(rhs_label, payload.two, element_bits, machine))
                out.text.extend(
                    check_dst_lines(expected, element_bits, machine=machine, label=dst_label)
                )
                out.data.extend(repeated_square_lines(dst_label, expected, element_bits, machine))
                out.data.append("")
