#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""mfrint*.ew whose integral result overflows the destination format.

Spec:    instruction_semantics.adoc:229-232, instruction_semantics.adoc:244-245
Quote:   `OF` is set when the rounded result's magnitude exceeds the destination's finite range.  Such a result also sets `NX`.
Checks:  every rounding instruction emits an overflowing stimulus for each destination format it can narrow into, and the stored element and amefflags must match the direction's IEEE 754-2019 7.4 overflow destination

M3 asked which value `mfrintz.ew` stores when the integral result does not fit
the destination: +inf or the largest finite value.  The answer follows from two
rules that the model and both simulators already implement for the ordinary
arithmetic path:

* the instruction's own direction governs the representational rounding
  (instructions.adoc:1516-1517), and
* an overflowing directed rounding is defined by IEEE 754-2019 7.4: toward zero
  takes every overflow to the largest finite magnitude, toward negative takes a
  positive overflow there and a negative overflow to -infinity, toward positive
  is the mirror image, and round-to-nearest delivers the infinity.

So `mfrintz(100000)` from FP64 into FP16 stores 65504 and raises `OF|NX`, not
+inf; `mfrintn` (round-to-nearest) stores +inf.  instruction_semantics.adoc:229-232
adds the one case the direction table cannot express: a destination without an
infinity encoding saturates, which is why every direction stores E4M3's 448.

E5M2 is deliberately absent.  QEMU stores the infinity where IEEE 754, the model
and spike store 0x7B (the two directed-toward-zero overflows), and that is the
separate QEMU item of `doc/Ztt未修问题清单261021.md` (Q2); locking it here would
turn the QEMU corpus run red for a defect this template cannot fix.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import TYPE_CHECKING

from mmul_gen.asm import check_dst_element_lines
from mmul_gen.float_formats import (
    CANONICAL_NAN,
    FFLAGS_OF,
    FFLAGS_NX,
    FORMATS,
    encode_exact,
    encode_overflow,
)
from mmul_gen.machine import FORMED_SOFTFLOAT, dtype_stem
from mmul_gen.mixed_math import MixedMathOperation
from mmul_gen.square_layout import (
    SquareGeometry,
    cycles,
    emit_square,
    geometry,
    sampled_indices,
    transfer_steps,
)
from mmul_gen.templates.base import Case, CaseOutput, Template, case_payload

if TYPE_CHECKING:  # pragma: no cover - typing only
    from mmul_gen.instruction import Instruction
    from mmul_gen.machine import DType, MachineConfig


#: The destination formats an overflowing stimulus can be built for, with the
#: sources wide enough to hold it.  FP64 cannot overflow from FP64, and a
#: destination without an infinity has no "toward the infinity" branch.
OVERFLOW_DESTINATIONS = (
    ("AME_FP16_DTYPE", ("AME_FP64_DTYPE", "AME_FP32_DTYPE")),
    ("AME_FP32_DTYPE", ("AME_FP64_DTYPE",)),
    ("AME_OCP_E4M3_DTYPE", ("AME_FP64_DTYPE", "AME_FP32_DTYPE")),
)


@dataclass(frozen=True)
class RoundingOverflowCase:
    """One overflowing rounding case: its operands, its answer, and its layout."""

    source_dtype: str
    destination_dtype: str
    source_values: tuple[int, ...]
    expected: tuple[int, ...]
    flags: int
    description: str
    geometry: SquareGeometry


class FloatRoundingOverflow(Template):
    """A rounding instruction whose result the destination cannot represent."""

    name = "float_rounding_overflow"
    dtypes = FORMED_SOFTFLOAT

    def __init__(self, operation: MixedMathOperation) -> None:
        """``operation`` is one of the four rounding operations of the family."""

        if operation not in {
            MixedMathOperation.FLOOR,
            MixedMathOperation.NEAREST,
            MixedMathOperation.CEIL,
            MixedMathOperation.TRUNC,
        }:
            raise ValueError(f"{operation}: not a rounding operation")
        self.operation = operation

    def _pairs(
        self, machine: "MachineConfig", destination_name: str | None = None
    ) -> tuple[tuple[str, str], ...]:
        available = {candidate.name for candidate in FORMED_SOFTFLOAT(machine)}
        pairs = []
        for destination, sources in OVERFLOW_DESTINATIONS:
            if destination not in available:
                continue
            if destination_name is not None and destination != destination_name:
                continue
            for source in sources:
                if source in available:
                    pairs.append((source, destination))
        return tuple(pairs)

    def fits(
        self, machine: "MachineConfig", instruction: "Instruction", dtype: DType | None
    ) -> bool:
        if dtype is None:
            return False
        return bool(self._pairs(machine, dtype.name))

    def build(
        self,
        machine: "MachineConfig",
        instruction: "Instruction",
        dtype: DType | None,
    ) -> tuple[Case, ...]:
        if dtype is None:
            raise ValueError("an overflow case is always formed from a datatype")
        cases = [
            Case(number=number, dtype=dtype, payload=payload, description=payload.description)
            for number, payload in enumerate(
                self._payload(machine, source, destination)
                for source, destination in self._pairs(machine, dtype.name)
            )
        ]
        return tuple(cases)

    def _payload(
        self, machine: "MachineConfig", source_name: str, destination_name: str
    ) -> RoundingOverflowCase:
        """The encoded stimulus and answer of one overflowing pair."""

        operation = self.operation
        placed = geometry(machine, FORMATS[source_name].bits, FORMATS[destination_name].bits)
        count = placed.nsq * machine.nelem
        # Both signs appear: the two sign-dependent branches of 7.4 are only
        # distinguishable on a negative overflow.
        threshold = Fraction(2) ** (FORMATS[destination_name].maximum_exponent + 1)
        stimulus = (threshold, -threshold)
        sources: list[int] = []
        answers: list[int] = []
        for value in stimulus:
            encoded = encode_exact(value, source_name)
            if encoded is None:
                raise ValueError(
                    f"{value} is not exactly representable in {source_name}; "
                    "an overflowing stimulus must be exact in the source"
                )
            expected, _ = encode_overflow(
                operation.exact_answer(value),
                destination_name,
                operation.rounding_direction,
            )
            sources.append(encoded)
            answers.append(expected)
        return RoundingOverflowCase(
            source_dtype=source_name,
            destination_dtype=destination_name,
            source_values=cycles(tuple(sources), count),
            expected=cycles(tuple(answers), count),
            flags=FFLAGS_OF | FFLAGS_NX,
            description=(
                f"{operation.value}: {dtype_stem(source_name)} -> "
                f"{dtype_stem(destination_name)}, overflowing"
            ),
            geometry=placed,
        )

    def render(
        self,
        machine: "MachineConfig",
        instruction: "Instruction",
        case: Case,
        out: CaseOutput,
    ) -> None:
        payload = case_payload(RoundingOverflowCase, case)
        source_format = FORMATS[payload.source_dtype]
        destination_format = FORMATS[payload.destination_dtype]
        placed = payload.geometry
        stem = (
            f"overflow{case.number}_"
            f"{dtype_stem(payload.source_dtype)}_to_{dtype_stem(payload.destination_dtype)}"
        )
        source_label = f"{stem}_source"
        seed_label = f"{stem}_seed"
        destination_label = f"{stem}_destination"
        source_steps = transfer_steps(
            machine, placed.nsq, source_format.bits, placed.source_base, source_label
        )
        seed_steps = transfer_steps(
            machine, placed.nsq, destination_format.bits, placed.destination_base, seed_label
        )
        destination_steps = transfer_steps(
            machine,
            placed.nsq,
            destination_format.bits,
            placed.destination_base,
            destination_label,
        )
        out.text.extend(
            [
                f"    # {instruction.name} {payload.description}",
                "    ame.release",
                "    li      t0, 0",
                "    ame.acquire t1, t0",
                "    EXPECT  t1, 1",
                "    csrwi   amestatus, 0",
            ]
        )
        for register_base, label in source_steps:
            out.text.extend(
                [
                    f"    li      t0, {payload.source_dtype}",
                    f"    msettyp m{register_base}, t0",
                    f"    la      t1, {label}",
                    f"    mls.rm     m{register_base}, t1",
                ]
            )
        for register_base, label in seed_steps:
            out.text.extend(
                [
                    f"    li      t0, {payload.destination_dtype}",
                    f"    msettyp m{register_base}, t0",
                    f"    la      t1, {label}",
                    f"    mls.rm     m{register_base}, t1",
                ]
            )
        out.text.extend(
            [
                "    csrw    amefflags, x0",
                f"    {instruction.name} m{placed.destination_base}, m{placed.source_base}",
                "    csrr    t5, amefflags",
                f"    EXPECT  t5, {payload.flags}",
                # An exceptional condition is a data result, not an unsupported
                # tuple (instruction_semantics.adoc:229-230).
                "    csrr    t2, amestatus",
                "    EXPECT  t2, 0",
            ]
        )
        for register_base, label in destination_steps:
            out.text.extend(
                [
                    f"    la      t2, {label}",
                    f"    mss.rm     m{register_base}, t2",
                ]
            )
        for index in sampled_indices(len(payload.expected)):
            out.text.extend(
                check_dst_element_lines(
                    payload.expected[index],
                    destination_format.bits,
                    index,
                    destination_label,
                )
            )
        emit_square(out, machine, source_label, payload.source_values, source_format.bits)
        emit_square(
            out,
            machine,
            seed_label,
            (CANONICAL_NAN[payload.destination_dtype],) * len(payload.source_values),
            destination_format.bits,
        )
        emit_square(out, machine, destination_label, payload.expected, destination_format.bits)
        out.data.append("")


__all__ = [
    "FloatRoundingOverflow",
    "OVERFLOW_DESTINATIONS",
    "RoundingOverflowCase",
]
