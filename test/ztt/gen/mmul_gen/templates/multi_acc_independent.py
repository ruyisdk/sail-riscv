#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""The independent multi-accumulator template."""

from __future__ import annotations

DOC_ZH = """\
独立多累加器模板。
"""

from typing import TYPE_CHECKING

from dataclasses import dataclass

from mmul_gen.asm import (
    check_dst_lines,
    repeated_square_lines,
)
from mmul_gen.machine import (
    DType,
    INTEGER,
    MachineConfig,
    dtype_stem,
)
from mmul_gen.reference import (
    MULTI_ACC_SEED_STEP,
    seeded_ones_product,
)
from mmul_gen.registers import (
    AccumulatorOperand,
    MRegisterRole,
    RegisterLayout,
    m_register_layouts,
)
from mmul_gen.templates.base import (

    Case,
    Template,
    case_payload,
    flatten,
)

if TYPE_CHECKING:
    from mmul_gen.instruction import Instruction


@dataclass(frozen=True)
class MultiAccumulatorPayload:
    """Independently seeded accumulators, one expected value each."""

    seeds: tuple[int, ...]
    expected: tuple[int, ...]


def _multi_acc_fits(machine: MachineConfig, dtype: DType) -> bool:
    return machine.num_acc_regs >= 2


class MultiAccIndependent(Template):
    """Every legal accumulator seeded, accumulated, and read independently."""

    summary_zh = "为每个合法累加器播种、累加并独立读回。"
    name = "multi_acc_independent"
    dtypes = INTEGER

    def fits(self, machine: MachineConfig, instruction: Instruction, dtype: DType) -> bool:
        return _multi_acc_fits(machine, dtype)

    def build(self, machine, instruction, dtype):
        count = machine.num_acc_regs
        seeds = tuple(MULTI_ACC_SEED_STEP * (index + 1) for index in range(count))
        expected = flatten(
            seeded_ones_product(seed, dtype.name, dtype.bits, machine.n) for seed in seeds
        )
        roles = (
            MRegisterRole("seed", machine.nregs(dtype.bits)),
            MRegisterRole("ones", machine.nregs(dtype.bits)),
            MRegisterRole("md", machine.nregs(dtype.bits), reuse_of="seed"),
        )
        all_accumulators = AccumulatorOperand(
            name="all_accumulators",
            description="all legal accumulators independently seeded and accumulated",
            base=0,
            span=count,
        )
        description = "每个合法累加器独立播种并累加"
        return [
            Case(
                number=0,
                dtype=dtype,
                layout=RegisterLayout(m=layout, acc=all_accumulators),
                payload=MultiAccumulatorPayload(seeds=seeds, expected=expected),
                description=description,
            )
            for layout in m_register_layouts(machine.num_m_regs, roles)
        ]

    def render(self, machine, instruction, case, out):
        payload = case_payload(MultiAccumulatorPayload, case)
        element_bits = case.dtype.bits
        if element_bits not in {8, 16, 32, 64}:
            raise ValueError(f"unsupported multi-accumulator element width: {element_bits}")

        seeds = payload.seeds
        expected = payload.expected
        count = len(seeds)
        if (case.layout.acc.base, case.layout.acc.span) != (0, count):
            raise AssertionError("multi-accumulator case has an invalid ACC layout")

        number = case.number
        stem = dtype_stem(case.dtype.name)
        seed_register = case.layout.m.base("seed")
        ones_register = case.layout.m.base("ones")
        destination = case.layout.m.base("md")
        prefix = f"mac{number}_{stem}_"
        ones_square = f"{prefix}ones_square"
        seed_squares = [f"{prefix}seed{index}_square" for index in range(count)]
        dst_squares = [f"{prefix}acc{index}_dst" for index in range(count)]

        out.text.extend(
            [
                f"    # case {number}: multi_acc_independent {case.dtype.name} on"
                f" acc0..acc{count - 1} of {machine.num_acc_regs}",
                f"    li      t0, {case.dtype.name}",
                f"    msettyp m{seed_register}, t0",
                f"    msettyp m{ones_register}, t0",
            ]
        )
        out.text.extend(f"    asettyp acc{index}, t0" for index in range(count))
        out.text.append("")
        out.text.extend(
            [
                f"    la      t1, {ones_square}",
                f"    mls.rm  m{ones_register}, t1",
            ]
        )
        for index, seed_label in enumerate(seed_squares):
            out.text.extend(
                [
                    f"    la      t1, {seed_label}",
                    f"    mls.rm  m{seed_register}, t1",
                    f"    mmov.a.m acc{index}, m{seed_register}",
                ]
            )
        for index in range(count):
            out.text.append(f"    {instruction.name} acc{index}, m{ones_register}, m{ones_register}")
        out.text.append("")
        for index, dst_label in enumerate(dst_squares):
            out.text.extend(
                [
                    f"    mmov.m.a m{destination}, acc{index}",
                    f"    la      t3, {dst_label}",
                    f"    mss.rm  m{destination}, t3",
                ]
            )
        out.text.append("")

        for dst_label, value in zip(dst_squares, expected):
            out.text.extend(
                check_dst_lines(value, element_bits, machine=machine, label=dst_label)
            )

        out.data.extend(repeated_square_lines(ones_square, 1, element_bits, machine))
        out.data.append("")
        for seed_label, seed in zip(seed_squares, seeds):
            out.data.extend(repeated_square_lines(seed_label, int(seed), element_bits, machine))
            out.data.append("")
        for dst_label in dst_squares:
            out.data.extend(repeated_square_lines(dst_label, 0, element_bits, machine))
            out.data.append("")


MULTI_ACC_INDEPENDENT = MultiAccIndependent()
