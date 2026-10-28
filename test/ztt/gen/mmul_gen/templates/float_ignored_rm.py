#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""mfrint*.ew executed with a destination rounding field the instruction ignores.

Spec:    instructions.adoc:1480-1482, 1515-1517, 1550-1552, 1585-1587
Quote:   For a standard floating-point operand, infinity is unchanged, zero preserves its sign, and a representable integral result is exact.  This instruction-specific rounding direction overrides the destination datatype rounding-mode field.
Checks:  every rounding instruction emits each tuple twice, once with the destination rounding-mode field set to RNE and once to RNO, and both runs must store the same bits, leave amestatus.UN clear and raise the same amefflags

The field is not merely advisory: ``datatypes.adoc:155-157`` gives ``0101`` an
encoding (RNO) without an algorithm, which is why the model answers an RNO
destination with ``amestatus.UN`` for an operation that *uses* the field.  For
the rounding family nothing reads it, so the tuple is legal and the only
observable difference an RNO field can make is the one this template forbids.

Each tuple therefore appears twice with an identical expectation: the pair *is*
the assertion "the RNO run is indistinguishable from the RNE run", and a model
that gates on the field fails the first run it reaches while a model that lets
the field steer the representation step fails the second.

Tuples: every format as a same-format pair (the field must not gate the tuple at
all), plus two narrowing pairs whose integral result needs a representational
rounding -- ``2049`` and ``2051`` sit on the fp16 grid's half-way points, so
there the direction that *does* apply is the instruction's own, not the field's.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import TYPE_CHECKING

from mmul_gen.asm import check_dst_element_lines
from mmul_gen.float_formats import (
    CANONICAL_NAN,
    FORMATS,
    FFLAGS_NX,
    encode_exact,
    encode_rounded,
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


#: The destination rounding-mode field of the second run.  ``AME_RND_RNO`` is the
#: assembler's name for bits 25:22 = 0101.
IGNORED_ROUNDING_FIELD = "AME_RND_RNO"

#: Same-format pairs: the field must not be able to gate the tuple.
SAME_FORMAT_TUPLES = tuple(
    (name, name)
    for name in (
        "AME_FP16_DTYPE",
        "AME_BF16_DTYPE",
        "AME_FP32_DTYPE",
        "AME_FP64_DTYPE",
        "AME_OCP_E4M3_DTYPE",
        "AME_OCP_E5M2_DTYPE",
    )
)

#: Narrowing pairs: the integral result is not representable in the destination,
#: so the representation step runs and must follow the instruction's direction.
NARROWING_TUPLES = (
    ("AME_FP64_DTYPE", "AME_FP16_DTYPE"),
    ("AME_FP32_DTYPE", "AME_FP16_DTYPE"),
)

#: Sources where each rounding direction gives a different integral answer.
DIRECTION_STIMULUS = (
    Fraction(3, 2),
    Fraction(-3, 2),
    Fraction(5, 2),
    Fraction(-5, 2),
)

#: Sources that are integral but not representable in fp16: the half-way points
#: between 2048 and 2050, and between 2050 and 2052.
NARROWING_STIMULUS = (
    Fraction(2049),
    Fraction(-2049),
    Fraction(2051),
    Fraction(-2051),
)


@dataclass(frozen=True)
class IgnoredRoundingCase:
    """One run of a rounding instruction with a decided rounding-mode field."""

    source_dtype: str
    destination_dtype: str
    rounding_field: str
    source_values: tuple[int, ...]
    expected: tuple[int, ...]
    flags: int
    description: str
    geometry: SquareGeometry


class FloatIgnoredRoundingMode(Template):
    """A rounding instruction whose destination field the instruction overrides."""

    name = "float_ignored_rounding_mode"
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

    def _tuples(self) -> tuple[tuple[str, str], ...]:
        return SAME_FORMAT_TUPLES + NARROWING_TUPLES

    def fits(
        self, machine: "MachineConfig", instruction: "Instruction", dtype: DType | None
    ) -> bool:
        """Whether this destination format has one feasible tuple."""

        if dtype is None:
            return False
        available = {candidate.name for candidate in FORMED_SOFTFLOAT(machine)}
        return any(
            source in available and destination in available
            for source, destination in self._tuples()
            if destination == dtype.name
        )

    def build(
        self,
        machine: "MachineConfig",
        instruction: "Instruction",
        dtype: DType | None,
    ) -> tuple[Case, ...]:
        if dtype is None:
            raise ValueError("a rounding case is always formed from a datatype")
        available = {candidate.name: candidate for candidate in FORMED_SOFTFLOAT(machine)}
        cases: list[Case] = []
        number = 0
        for source_name, destination_name in self._tuples():
            if destination_name != dtype.name:
                continue
            if source_name not in available or destination_name not in available:
                continue
            for field in ("", IGNORED_ROUNDING_FIELD):
                payload = self._payload(
                    machine, available[source_name], available[destination_name], field
                )
                cases.append(
                    Case(
                        number=number,
                        dtype=dtype,
                        payload=payload,
                        description=payload.description,
                    )
                )
                number += 1
        return tuple(cases)

    def _payload(
        self,
        machine: "MachineConfig",
        source: "DType",
        destination: "DType",
        rounding_field: str,
    ) -> IgnoredRoundingCase:
        """The encoded stimulus and answer of one run."""

        operation = self.operation
        placed = geometry(machine, source.bits, destination.bits)
        count = placed.nsq * machine.nelem
        stimuli = DIRECTION_STIMULUS
        if (source.name, destination.name) in NARROWING_TUPLES:
            stimuli = DIRECTION_STIMULUS + NARROWING_STIMULUS
        sources: list[int] = []
        answers: list[int] = []
        inexact = False
        for value in stimuli:
            encoded = _encode_source(value, source.name)
            answer = operation.exact_answer(value)
            expected, rounded = encode_rounded(
                answer, destination.name, operation.rounding_direction
            )
            inexact = inexact or rounded
            sources.append(encoded)
            answers.append(expected)
        field = f" | {rounding_field}" if rounding_field else ""
        return IgnoredRoundingCase(
            source_dtype=source.name,
            destination_dtype=destination.name,
            rounding_field=field,
            source_values=cycles(tuple(sources), count),
            expected=cycles(tuple(answers), count),
            flags=FFLAGS_NX if inexact else 0,
            description=(
                f"{operation.value}: {dtype_stem(source.name)} -> "
                f"{dtype_stem(destination.name)}, rounding field "
                f"{'RNO (ignored)' if rounding_field else 'RNE'}"
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
        payload = case_payload(IgnoredRoundingCase, case)
        source_format = FORMATS[payload.source_dtype]
        destination_format = FORMATS[payload.destination_dtype]
        placed = payload.geometry
        stem = (
            f"ignored{case.number}_"
            f"{dtype_stem(payload.source_dtype)}_to_{dtype_stem(payload.destination_dtype)}"
            f"{'_rno' if payload.rounding_field else ''}"
        )
        source_label = f"{stem}_source"
        seed_label = f"{stem}_seed"
        destination_label = f"{stem}_destination"
        source_steps = transfer_steps(
            machine, placed.nsq, source_format.bits, placed.source_base, source_label
        )
        destination_steps = transfer_steps(
            machine,
            placed.nsq,
            destination_format.bits,
            placed.destination_base,
            destination_label,
        )
        seed_steps = transfer_steps(
            machine,
            placed.nsq,
            destination_format.bits,
            placed.destination_base,
            seed_label,
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
                    f"    li      t0, {payload.destination_dtype}{payload.rounding_field}",
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
                # The rounding field must not turn the tuple into an
                # unsupported one; the store below proves the destination was
                # actually written, not left at its seeded NaN.
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
        emit_square(
            out,
            machine,
            destination_label,
            payload.expected,
            destination_format.bits,
        )
        out.data.append("")


def _encode_source(value: Fraction, dtype_name: str) -> int:
    """The stored bits of a source value, which every tuple holds exactly."""

    encoded = encode_exact(value, dtype_name)
    if encoded is None:
        raise ValueError(f"{value} is not exactly representable in {dtype_name}")
    return encoded


__all__ = [
    "DIRECTION_STIMULUS",
    "IGNORED_ROUNDING_FIELD",
    "FloatIgnoredRoundingMode",
    "IgnoredRoundingCase",
    "NARROWING_STIMULUS",
    "NARROWING_TUPLES",
    "SAME_FORMAT_TUPLES",
]
