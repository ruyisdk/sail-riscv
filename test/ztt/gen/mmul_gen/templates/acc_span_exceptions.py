#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""The two boundary paths of the packed accumulator span.

Both are "the transfer must not happen" tests, and each is checked with the same
discipline as a positive test:

* ``pack_factor`` greater than the accumulator file sets ``amestatus.UN`` and
  writes nothing -- proven by reading the destination back and finding the whole
  poison image intact.
* a span crossing the end of the file is an Illegal Instruction with no partial
  write -- proven through the trap guard, then by reading *every* accumulator of
  the span back: the one accumulator the case deliberately clears reads as zero,
  everything else still reads as poison.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from mmul_gen.asm import check_dst_lines
from mmul_gen.machine import PACKED_INTEGER, MachineConfig, dtype_stem
from mmul_gen.registers import AccumulatorOperand, RegisterLayout, packed_span_cases
from mmul_gen.templates.acc_span_common import (
    corrupt_value,
    packed_pack_factor,
    poison_value,
    square_checks,
    uniform_image,
)
from mmul_gen.templates.base import Case, CaseOutput, Template

if TYPE_CHECKING:
    from mmul_gen.instruction import Instruction
    from mmul_gen.machine import DType


#: Declared input cases; each selects one of the two boundary paths.
UNSUPPORTED_SPAN = "unsupported_span"
CROSSING_SPAN = "crossing_span"


@dataclass(frozen=True)
class SpanException:
    """One boundary case of the shared exception recipe."""

    case_id: int
    #: ``True`` for the ``amestatus.UN`` path, ``False`` for the illegal span.
    unsupported: bool
    #: This pseudo-case only arms the trap guard; it tests nothing itself.
    guard: bool = False
    #: The crossing span, absent on the ``amestatus.UN`` path.
    illegal: AccumulatorOperand | None = None
    #: Accumulator bases the poison image is written to before the illegal move.
    fill_bases: tuple[int, ...] = ()
    #: Traps already expected earlier in the file; the guard counts from there.
    traps_before: int = 0


class AccumulatorSpanExceptions(Template):
    """Emit the ``amestatus.UN`` and illegal-span boundary paths."""

    name = "acc_span_exceptions"
    dtypes = PACKED_INTEGER

    def __init__(self, *cases: str) -> None:
        """``cases`` are the exception case names this recipe is enabled to emit."""

        self.input_cases = tuple(cases)

    def build(
        self, machine: MachineConfig, instruction: Instruction, dtype: DType | None
    ) -> Sequence[Case]:
        if dtype is None:
            raise ValueError("a span exception case is always formed from a datatype")
        domain = self.dtypes(machine)
        index = domain.index(dtype)
        enabled = set(self.input_cases)
        pack = packed_pack_factor(machine, dtype.bits)
        unsupported = pack > machine.num_acc_regs

        # The trap ordinal counts the two expected traps of every earlier
        # illegal span, so it is a property of the file, not of one case.
        traps_before = 2 * sum(
            1
            for earlier in domain[:index]
            if packed_pack_factor(machine, earlier.bits) <= machine.num_acc_regs
        )
        if unsupported:
            if UNSUPPORTED_SPAN not in enabled:
                return ()
            payload = SpanException(
                case_id=index,
                unsupported=True,
                fill_bases=(),
                traps_before=traps_before,
            )
            return (*self._guard_cases(machine, index, dtype), Case(number=0, dtype=dtype, payload=payload))

        if CROSSING_SPAN not in enabled:
            return ()
        illegal = next(
            (
                case
                for case in packed_span_cases(machine.num_acc_regs, pack)
                if not case.legal
            ),
            None,
        )
        if illegal is None:
            raise AssertionError(f"no crossing packed span case for pack factor {pack}")
        payload = SpanException(
            case_id=index,
            unsupported=False,
            illegal=illegal,
            fill_bases=tuple(range(0, machine.num_acc_regs, pack)),
            traps_before=traps_before,
        )
        return (
            *self._guard_cases(machine, index, dtype),
            Case(
                number=0,
                dtype=dtype,
                payload=payload,
                layout=RegisterLayout(acc=illegal),
            ),
        )

    def _guard_cases(
        self, machine: MachineConfig, index: int, dtype: DType
    ) -> tuple[Case, ...]:
        """The trap guard this file arms once, before its first real case.

        The guard is armed at the top of the file, after the file-level
        ``# input:`` block; the driver has already emitted that block, so the
        guard rides in front of the first datatype's case.  An implementation
        with a single accumulator file cannot trap at all, so it is skipped.
        """

        if index != 0 or machine.num_acc_regs < 2:
            return ()
        return (
            Case(
                number=0,
                dtype=dtype,
                payload=SpanException(
                    case_id=index, unsupported=False, guard=True, traps_before=0
                ),
            ),
        )

    def render(
        self,
        machine: MachineConfig,
        instruction: Instruction,
        case: Case,
        out: CaseOutput,
    ) -> None:
        if case.dtype is None or not isinstance(case.payload, SpanException):
            raise ValueError("span exception case is missing its datatype or payload")
        payload = case.payload
        dtype = case.dtype
        if payload.guard:
            out.text.extend(["    TRAP_GUARD_ARM", ""])
            return
        if payload.unsupported:
            self._render_unsupported(machine, dtype, payload, out)
        else:
            self._render_crossing(machine, dtype, payload, out)

    def _render_unsupported(
        self,
        machine: MachineConfig,
        dtype: DType,
        payload: SpanException,
        out: CaseOutput,
    ) -> None:
        element_bits = dtype.bits
        pack = packed_pack_factor(machine, element_bits)
        poison = poison_value(element_bits)
        prefix = f"exc{payload.case_id}_{dtype_stem(dtype.name)}_"
        img_v = f"{prefix}poison"
        dst = f"{prefix}dst"
        out.text.extend(
            [
                f"    # case {payload.case_id}: {dtype.name} pack_factor={pack} >"
                f" {machine.num_acc_regs} acc registers -> amestatus.UN",
                f"    li      t0, {dtype.name}",
                "    msettyp m0, t0",
                "    msettyp m1, t0",
                "    asettyp acc0, t0",
                f"    la      t1, {img_v}",
                "    mls.rm  m1, t1",
                "    csrwi   amestatus, 0",
                "    mmov.m.a m1, acc0",
                "    csrr    t2, amestatus",
                "    EXPECT  t2, 1",
                f"    la      t3, {dst}",
                "    mss.rm  m1, t3",
                *check_dst_lines(poison, element_bits, machine=machine, label=dst),
                "    csrwi   amestatus, 0",
                "    mmov.a.m acc0, m1",
                "    csrr    t2, amestatus",
                "    EXPECT  t2, 1",
                "",
            ]
        )
        out.data.extend(uniform_image(img_v, poison, element_bits, machine))
        out.data.extend(uniform_image(dst, 0, element_bits, machine))

    def _render_crossing(
        self,
        machine: MachineConfig,
        dtype: DType,
        payload: SpanException,
        out: CaseOutput,
    ) -> None:
        if payload.illegal is None:
            raise ValueError("the illegal span case is missing its accumulator span")
        element_bits = dtype.bits
        illegal = payload.illegal
        pack = illegal.span
        base = illegal.base
        poison = poison_value(element_bits)
        corrupt = corrupt_value(element_bits)
        prefix = f"exc{payload.case_id}_{dtype_stem(dtype.name)}_"
        img_v = f"{prefix}poison"
        img_b = f"{prefix}corrupt"
        dst = f"{prefix}dst"

        lines = [
            f"    # case {payload.case_id}: {dtype.name} span acc{base}.."
            f"acc{base + pack - 1} crosses {machine.num_acc_regs} accumulators ->"
            " Illegal Instruction, no partial write",
            f"    li      t0, {dtype.name}",
            "    msettyp m0, t0",
            "    msettyp m1, t0",
            "    msettyp m2, t0",
        ]
        for fill_base in payload.fill_bases:
            lines.extend(
                [
                    f"    la      t1, {img_v}",
                    "    mls.rm  m0, t1",
                    f"    asettyp acc{fill_base}, t0",
                    f"    mmov.a.m acc{fill_base}, m0",
                ]
            )
        lines.extend(
            [
                f"    la      t1, {img_v}",
                "    mls.rm  m1, t1",
                f"    li      t0, {dtype.name}",
                # Retyping the illegal base clears that one accumulator
                # (asettyp is a raw clear); the re-read below expects exactly
                # that zero square and poison everywhere else.
                f"    asettyp acc{base}, t0",
                f"    la      t1, {img_b}",
                "    mls.rm  m0, t1",
                f"    mmov.a.m acc{base}, m0",
                f"    EXPECT_TRAP {payload.traps_before + 1}",
                f"    mmov.m.a m1, acc{base}",
                f"    EXPECT_TRAP {payload.traps_before + 2}",
                "",
                f"    li      t0, {dtype.name}",
            ]
        )
        for read_base in payload.fill_bases:
            read_label = f"{prefix}rd{read_base}"
            square_values = [
                0 if read_base + square == base else poison for square in range(pack)
            ]
            lines.extend(
                [
                    f"    mmov.m.a m2, acc{read_base}",
                    f"    la      t3, {read_label}",
                    "    mss.rm  m2, t3",
                    *square_checks(square_values, element_bits, machine, read_label),
                ]
            )
        lines.extend(
            [
                f"    la      t3, {dst}",
                "    mss.rm  m1, t3",
                *check_dst_lines(poison, element_bits, machine=machine, label=dst),
            ]
        )
        out.text.extend(lines)

        out.data.extend(uniform_image(img_v, poison, element_bits, machine))
        out.data.extend(uniform_image(img_b, corrupt, element_bits, machine))
        out.data.extend(uniform_image(dst, 0, element_bits, machine))
        for read_base in payload.fill_bases:
            read_label = f"{prefix}rd{read_base}"
            out.data.extend(
                uniform_image(read_label, poison, element_bits, machine)
            )


__all__ = [
    "AccumulatorSpanExceptions",
    "CROSSING_SPAN",
    "SpanException",
    "UNSUPPORTED_SPAN",
]
