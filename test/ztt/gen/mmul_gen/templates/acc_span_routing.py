#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Data and routing proof for a packed accumulator span.

One M image is moved into a span of accumulators, a *second* overlapping image
is moved into an adjacent span, and both spans are read back.  The overlapping
write is what pins every accumulator of the span down: a transfer that landed in
the wrong accumulator would show up in the second read-back.

The expected images are not written out by hand.  ``build`` keeps the physical
map of which square each accumulator holds, so the read-back expectations are a
consequence of the selected span bases -- including where the two spans overlap.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from mmul_gen.asm import repeated_square_lines, square_lines
from mmul_gen.case_description import description
from mmul_gen.machine import PACKED_INTEGER, MachineConfig, dtype_stem
from mmul_gen.registers import (
    AccumulatorOperand,
    MRegisterRole,
    RegisterLayout,
    m_register_layouts,
    packed_span_cases,
)
from mmul_gen.templates.acc_span_common import (
    flat_square,
    packed_pack_factor,
    span_a_value,
    span_b_value,
    square_checks,
)
from mmul_gen.templates.base import Case, CaseOutput, Template

if TYPE_CHECKING:
    from mmul_gen.instruction import Instruction
    from mmul_gen.machine import DType


#: Declared input cases that select which span bases are exercised.
OVERLAPPING_READBACK = "overlapping_readback"


@dataclass(frozen=True)
class SpanRouting:
    """One routing case: which accumulators hold which square image."""

    description: str
    primary: AccumulatorOperand
    secondary_base: int | None
    squares_a: tuple[int, ...]
    squares_b: tuple[int, ...]
    read1: tuple[int, ...]
    read2: tuple[int, ...]
    pack_factor: int
    descriptor_tag_base: int | None


class AccumulatorSpanRouting(Template):
    """Emit the write-overlap-read proof of one packed accumulator span."""

    name = "acc_span_routing"
    dtypes = PACKED_INTEGER

    def __init__(self, *cases: str) -> None:
        """``cases`` are the span case names this recipe is enabled to emit."""

        self.input_cases = tuple(cases)

    def fits(
        self,
        machine: MachineConfig,
        instruction: Instruction,
        dtype: DType | None = None,
    ) -> bool:
        if dtype is None:
            raise ValueError("a packed span case is always formed from a datatype")
        # A span that does not fit the accumulator file is the exception test's
        # subject, not this recipe's.
        return packed_pack_factor(machine, dtype.bits) <= machine.num_acc_regs

    def build(
        self, machine: MachineConfig, instruction: Instruction, dtype: DType | None
    ) -> Sequence[Case]:
        if dtype is None:
            raise ValueError("a packed span case is always formed from a datatype")
        pack = packed_pack_factor(machine, dtype.bits)
        squares_a = [span_a_value(square, dtype.bits) for square in range(pack)]
        squares_b = [
            span_b_value(square, dtype.bits, pack) for square in range(pack)
        ]
        legal_cases = [
            case for case in packed_span_cases(machine.num_acc_regs, pack) if case.legal
        ]
        enabled = set(self.input_cases)
        selected = {case.name for case in legal_cases if case.name in enabled}
        if OVERLAPPING_READBACK in enabled:
            selected = {case.name for case in legal_cases}
        nregs = machine.nregs(dtype.bits)

        cases: list[Case] = []
        for primary in legal_cases:
            if primary.name not in selected:
                continue
            secondary_base = None
            if OVERLAPPING_READBACK in enabled:
                if primary.base + 1 + pack <= machine.num_acc_regs:
                    secondary_base = primary.base + 1
                elif primary.base > 0:
                    secondary_base = primary.base - 1

            roles = [MRegisterRole("ms", nregs), MRegisterRole("md1", nregs)]
            if secondary_base is not None:
                roles.append(MRegisterRole("md2", nregs))

            # Apply the second image after the first one: keeping the physical
            # map here makes the overlap expectations a consequence of the
            # selected bases instead of a parallel hand-written list.
            physical: list[int | None] = [None] * machine.num_acc_regs
            for index, value in enumerate(squares_a):
                physical[primary.base + index] = value
            if secondary_base is not None:
                for index, value in enumerate(squares_b):
                    physical[secondary_base + index] = value

            read1 = tuple(
                physical[primary.base + index] for index in range(pack)
            )
            if any(value is None for value in read1):
                raise AssertionError("primary packed span has an uninitialized square")
            read2 = (
                tuple(
                    physical[secondary_base + index] for index in range(pack)
                )
                if secondary_base is not None
                else ()
            )
            if any(value is None for value in read2):
                raise AssertionError("secondary packed span has an uninitialized square")

            descriptor_tag_base: int | None = None
            if secondary_base is not None:
                if secondary_base > primary.base:
                    # The new high endpoint belongs only to the second span.
                    descriptor_tag_base = secondary_base + pack - 1
                else:
                    # The primary span's high endpoint lies outside the
                    # downward-overlapping second span.
                    descriptor_tag_base = primary.base + pack - 1

            span_description = (
                f"{description(primary.name)}: {primary.register_text}"
                + (
                    f"; overlapping readback {secondary_base}.."
                    f"{secondary_base + pack - 1}"
                    if secondary_base is not None
                    else ", no adjacent legal span"
                )
            )
            for layout in m_register_layouts(machine.num_m_regs, tuple(roles)):
                cases.append(
                    Case(
                        number=0,
                        dtype=dtype,
                        payload=SpanRouting(
                            description=span_description,
                            primary=primary,
                            secondary_base=secondary_base,
                            squares_a=tuple(squares_a),
                            squares_b=tuple(squares_b),
                            read1=read1,
                            read2=read2,
                            pack_factor=pack,
                            descriptor_tag_base=descriptor_tag_base,
                        ),
                        layout=RegisterLayout(m=layout, acc=primary),
                        description=span_description,
                    )
                )
        return cases

    def render(
        self,
        machine: MachineConfig,
        instruction: Instruction,
        case: Case,
        out: CaseOutput,
    ) -> None:
        if case.dtype is None or not isinstance(case.payload, SpanRouting):
            raise ValueError("packed span case is missing its datatype or payload")
        if case.layout is None or case.layout.m is None:
            raise ValueError("packed span case is missing its M-register layout")
        payload = case.payload
        dtype = case.dtype
        pack = payload.pack_factor
        primary_base = payload.primary.base
        secondary_base = payload.secondary_base
        descriptor_tag_base = payload.descriptor_tag_base
        source_reg = case.layout.group_base("ms")
        destination_reg1 = case.layout.group_base("md1")
        destination_reg2 = case.layout.group_base("md2") if secondary_base is not None else None
        uds_dtype = f"AME_UINT{machine.uds}_DTYPE"
        # The labels and the ``# case`` comment number cases across the whole
        # file, which is what the driver's case counter is.
        case_id = case.number
        prefix = f"span{case_id}_{dtype_stem(dtype.name)}_"
        img_a = f"{prefix}imgA"
        img_b = f"{prefix}imgB"
        rd1 = f"{prefix}rd1"
        rd2 = f"{prefix}rd2"

        lines = [
            f"    # case {case_id}: {instruction.name} {dtype.name} "
            f"pack_factor={pack} spans {payload.primary.register_text} of "
            f"{machine.num_acc_regs} accumulators",
        ]
        if secondary_base is not None:
            lines.extend(
                [
                    f"    li      t0, {uds_dtype}",
                    f"    asettyp acc{descriptor_tag_base}, t0",
                ]
            )
        lines.extend(
            [
                f"    li      t0, {dtype.name}",
                f"    msettyp m{source_reg}, t0",
                f"    msettyp m{destination_reg1}, t0",
            ]
        )
        if destination_reg2 is not None:
            lines.append(f"    msettyp m{destination_reg2}, t0")
        lines.append(f"    asettyp acc{primary_base}, t0")
        if secondary_base is not None:
            lines.append(f"    asettyp acc{secondary_base}, t0")
        lines.extend(
            [
                f"    la      t1, {img_a}",
                f"    mls.rm  m{source_reg}, t1",
                f"    mmov.a.m acc{primary_base}, m{source_reg}",
            ]
        )
        if secondary_base is not None:
            lines.extend(
                [
                    f"    la      t1, {img_b}",
                    f"    mls.rm  m{source_reg}, t1",
                    f"    mmov.a.m acc{secondary_base}, m{source_reg}",
                    f"    agettyp t1, acc{secondary_base}",
                    f"    EXPECT  t1, {dtype.name}",
                    f"    agettyp t2, acc{descriptor_tag_base}",
                    f"    EXPECT  t2, {uds_dtype}",
                ]
            )
        lines.extend(
            [
                f"    mmov.m.a m{destination_reg1}, acc{primary_base}",
                f"    la      t3, {rd1}",
                f"    mss.rm  m{destination_reg1}, t3",
                *square_checks(list(payload.read1), dtype.bits, machine, rd1),
            ]
        )
        if secondary_base is not None:
            lines.extend(
                [
                    f"    mmov.m.a m{destination_reg2}, acc{secondary_base}",
                    f"    la      t3, {rd2}",
                    f"    mss.rm  m{destination_reg2}, t3",
                    *square_checks(list(payload.read2), dtype.bits, machine, rd2),
                ]
            )
        out.text.extend(lines)
        out.data.extend(
            square_lines(
                img_a, flat_square(list(payload.squares_a), machine.nelem), dtype.bits, machine
            )
        )
        out.data.append("")
        out.data.extend(
            square_lines(
                img_b, flat_square(list(payload.squares_b), machine.nelem), dtype.bits, machine
            )
        )
        out.data.append("")
        out.data.extend(repeated_square_lines(rd1, 0, dtype.bits, machine))
        out.data.append("")
        if secondary_base is not None:
            out.data.extend(repeated_square_lines(rd2, 0, dtype.bits, machine))
            out.data.append("")


__all__ = ["OVERLAPPING_READBACK", "AccumulatorSpanRouting", "SpanRouting"]
