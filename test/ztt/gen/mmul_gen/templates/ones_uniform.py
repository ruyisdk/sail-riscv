#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""The all-ones product templates.

``OnesUniform128`` reuses ``OnesUniform``'s case builder and replaces only
the renderer, the datatype domain, and the resource predicate."""

from __future__ import annotations

from typing import TYPE_CHECKING

from dataclasses import dataclass

from mmul_gen.asm import (
    check_dst_lines,
    data_directive,
    hex_value,
    load_byte_lines,
    repeated_square_lines,
)
from mmul_gen.machine import (
    DType,
    INTEGER,
    INTEGER128,
    MachineConfig,
    dtype_stem,
)
from mmul_gen.reference import uniform_ones_product
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
class OnesUniformPayload:
    """Both sources are all ones; every destination element equals ``expected``."""

    expected: int


class OnesUniform(Template):
    """All-ones integer product with a cleared accumulator."""

    name = "ones_uniform"
    dtypes = INTEGER

    def build(self, machine, instruction, dtype):
        expected = uniform_ones_product(dtype.name, dtype.bits, machine.n)
        return paired_cases(machine, dtype, OnesUniformPayload(expected=expected))

    def render(self, machine, instruction, case, out):
        payload = case_payload(OnesUniformPayload, case)
        element_bits = case.dtype.bits
        if element_bits not in {8, 16, 32, 64}:
            raise ValueError(f"unsupported uniform-product element width: {element_bits}")

        directive = data_directive(element_bits)
        elem_bytes = element_bits // 8
        square_bytes = machine.nelem * elem_bytes
        expected_byte = int(hex_value(payload.expected, element_bits), 16) & 0xFF
        number = case.number
        stem = dtype_stem(case.dtype.name)
        lhs = register("ms1", case.layout)
        rhs = register("ms2", case.layout)
        destination = register("md", case.layout)
        acc = case.layout.acc.base
        a_square = f"case{number}_{stem}_a_square"
        b_square = f"case{number}_{stem}_b_square"
        c_square = f"case{number}_{stem}_c_square"

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
                f"    la      t3, {c_square}",
                f"    mss.rm     m{destination}, t3",
                "",
            ]
        )
        out.text.extend(
            [
                f"    la      t4, {c_square}",
                "    lbu     t5, 0(t4)",
                f"    EXPECT  t5, {expected_byte}",
                f"    lbu     t5, {elem_bytes}(t4)",
                f"    EXPECT  t5, {expected_byte}",
                *load_byte_lines("t5", "t4", square_bytes - elem_bytes),
                f"    EXPECT  t5, {expected_byte}",
                "",
            ]
        )
        out.text.append("")

        out.data.extend(
            [
                f".balign {square_bytes}",
                f"{a_square}:",
                f"    .rept {machine.nelem}",
                f"    {directive} 1",
                "    .endr",
                f".balign {square_bytes}",
                f"{b_square}:",
                f"    .rept {machine.nelem}",
                f"    {directive} 1",
                "    .endr",
                f".balign {square_bytes}",
                f"{c_square}:",
                f"    .rept {square_bytes}",
                "    .byte 0xa5",
                "    .endr",
                "",
            ]
        )


class OnesUniform128(OnesUniform):
    """All-ones 128-bit integer product spanning several M registers."""

    name = "ones_uniform_128"
    dtypes = INTEGER128

    def fits(self, machine: MachineConfig, instruction: Instruction, dtype: DType) -> bool:
        return two_register_groups_fit(machine, dtype)

    def render(self, machine, instruction, case, out):
        payload = case_payload(OnesUniformPayload, case)
        element_bits = case.dtype.bits
        if element_bits != 128:
            raise ValueError(f"unsupported 128-bit product width: {element_bits}")

        number = case.number
        stem = dtype_stem(case.dtype.name)
        source = register("ms1", case.layout)
        destination = register("md", case.layout)
        operand = register("ms2", case.layout)
        acc = case.layout.acc.base
        one_square = f"case{number}_{stem}_one_square"

        out.text.extend(
            [
                f"    # case {number}: {instruction.name} 128-bit {case.dtype.name}",
                f"    li      t0, {case.dtype.name}",
                f"    msettyp m{source}, t0",
                f"    msettyp m{operand}, t0",
                f"    asettyp acc{acc}, t0",
                "",
                f"    mzero.2d.acc acc{acc}",
                f"    la      t1, {one_square}",
                f"    mls.rm     m{destination}, t1",
                f"    la      t2, {one_square}",
                f"    mls.rm     m{operand}, t2",
                f"    {instruction.name} acc{acc}, m{source}, m{operand}",
                f"    mmov.m.a m{destination}, acc{acc}",
                "    la      t3, dst_square",
                f"    mss.rm     m{destination}, t3",
            ]
        )
        out.text.extend(check_dst_lines(payload.expected, element_bits, machine=machine))

        out.data.extend(repeated_square_lines(one_square, 1, element_bits, machine))
        out.data.append("")


ONES_UNIFORM = OnesUniform()
ONES_UNIFORM_128 = OnesUniform128()
