#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Mixed floating-point format tuples of the 1-D math family.

Spec:    instruction_semantics.adoc:181-183 (§6.2.2)
Quote:   "Among standard datatypes, mexp2.ew, mlog2.ew, mcos.ew, msin.ew, mtanh.ew, mrec.ew,
         mrsqrt.ew, msqrt.ew, and the mfrint*.ew family require floating-point source and
         destination datatypes."
Checks:  a source square written in one floating-point format and a destination square written in
         another one must execute (never report the tuple unsupported) and must deliver the value
         §6.2.3 defines for that tuple; the exactly representable cases are compared bit for bit,
         the bounded-approximation ones assert the must-set flags and a finite result instead

§6.2.2 constrains the family to floating-point *datatypes*; it never asks the
two operand datatypes to be the same format, and §6.2.3 rounds "a finite result
once using the destination datatype's rounding mode".  This template is the
tuple coverage that follows from those two sentences: every case writes its
source square in the source format and its destination square in the
destination format, so a model that rejects the mixed tuple leaves the seeded
destination untouched and fails, and a model that rounds through the wrong
format fails the exact cases.

Which stimulus a case uses is decided by the operation, not by the pair:

* ``mfrint{m,n,p,z}.ew``, ``msqrt.ew``, ``mexp2.ew`` and ``mlog2.ew`` have an
  exactly representable answer for a carefully chosen source, so their cases
  compare the stored element byte for byte.
* ``mrec.ew``, ``mrsqrt.ew``, ``mcos.ew``, ``msin.ew`` and ``mtanh.ew`` are
  bounded approximations whose last bits belong to the implementation, so their
  cases assert the flag such an operation must raise (NX) and that the delivered
  element is a finite number, and do not pretend to know the value.

The ``mfrint`` stimulus stays integral on purpose.  Which *direction* those
four instructions round a fractional source in is a separate behavior the
implementations do not agree about (an instruction-specific rounding direction
against the destination datatype's rounding-mode field), so asserting a
fractional result here would assert one implementation's reading rather than
the tuple rule this template covers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import TYPE_CHECKING

from mmul_gen.asm import check_dst_element_lines, load_byte_lines, square_lines
from mmul_gen.float_formats import (
    CANONICAL_NAN,
    FINITE_LIMIT_BYTE,
    FORMATS,
    encode_exact,
)
from mmul_gen.mixed_math import MixedMathOperation

#: ``amefflags.NX``: the result was rounded.
FFLAGS_NX = 0x01
from mmul_gen.machine import FORMED_SOFTFLOAT, dtype_stem
from mmul_gen.templates.base import Case, CaseOutput, Template, case_payload

if TYPE_CHECKING:  # pragma: no cover - typing only
    from mmul_gen.instruction import Instruction
    from mmul_gen.machine import DType, MachineConfig


#: The (source, destination) tuples the family has to execute.  Both directions
#: of a narrowing and a widening tuple appear for every format §6.2.2 lists, so
#: each format is exercised as a source and as a destination.
MIXED_FORMAT_PAIRS = (
    ("AME_FP64_DTYPE", "AME_FP16_DTYPE"),
    ("AME_FP64_DTYPE", "AME_FP32_DTYPE"),
    ("AME_FP32_DTYPE", "AME_FP16_DTYPE"),
    ("AME_FP64_DTYPE", "AME_BF16_DTYPE"),
    ("AME_FP32_DTYPE", "AME_OCP_E4M3_DTYPE"),
    ("AME_FP16_DTYPE", "AME_OCP_E5M2_DTYPE"),
    ("AME_FP16_DTYPE", "AME_FP64_DTYPE"),
    ("AME_FP32_DTYPE", "AME_FP64_DTYPE"),
    ("AME_BF16_DTYPE", "AME_FP64_DTYPE"),
    ("AME_FP16_DTYPE", "AME_FP32_DTYPE"),
    ("AME_BF16_DTYPE", "AME_FP32_DTYPE"),
    ("AME_OCP_E4M3_DTYPE", "AME_FP16_DTYPE"),
)








def _pack_factor(machine: "MachineConfig", element_bits: int) -> int:
    """How many logical squares one physical register holds for a format."""

    return machine.storage_elements(element_bits) // machine.nelem


def _cycles(values: tuple[int, ...], count: int) -> tuple[int, ...]:
    """``count`` elements taken from a short value roster, in order."""

    if not values:
        raise ValueError("a mixed-format square needs at least one value")
    return tuple(values[index % len(values)] for index in range(count))


@dataclass(frozen=True)
class MixedFormatGeometry:
    """The register groups and logical-square count one format pair needs."""

    source_base: int
    destination_base: int
    nsq: int


@dataclass(frozen=True)
class MixedFormatCase:
    """One decided mixed-format case: its operands, its answer, and its layout."""

    source_dtype: str
    destination_dtype: str
    source_values: tuple[int, ...]
    expected: tuple[int, ...]
    flags: int
    exact: bool
    description: str
    geometry: MixedFormatGeometry


def _register_group(
    num_m_regs: int, span: int, preferred: int, occupied: list[tuple[int, int]]
) -> int:
    """An aligned M-register group of ``span`` registers that is free."""

    if span > num_m_regs:
        raise ValueError(f"a {span}-register operand does not fit in {num_m_regs}")
    candidates = [
        base
        for base in range(0, num_m_regs - span + 1, span)
        if all(base + span <= low or high <= base for low, high in occupied)
    ]
    if not candidates:
        raise ValueError(
            f"no free group of {span} M registers in a file of {num_m_regs}"
        )
    return preferred if preferred in candidates else candidates[0]


class FloatMixedFormat(Template):
    """One source and one destination floating-point format that differ."""

    name = "float_mixed_format"
    dtypes = FORMED_SOFTFLOAT

    def __init__(self, operation: MixedMathOperation) -> None:
        """``operation`` is the instruction's own operation of the family."""

        self.operation = operation

    def _available(self, machine: "MachineConfig") -> dict[str, DType]:
        return {dtype.name: dtype for dtype in FORMED_SOFTFLOAT(machine)}

    def _span(self, machine: "MachineConfig", element_bits: int, nsq: int) -> int:
        return nsq * machine.nregs(element_bits)

    def _geometry(
        self,
        machine: "MachineConfig",
        source_bits: int,
        destination_bits: int,
    ) -> MixedFormatGeometry:
        nsq = max(_pack_factor(machine, source_bits), _pack_factor(machine, destination_bits))
        source_span = self._span(machine, source_bits, nsq)
        destination_span = self._span(machine, destination_bits, nsq)
        source_base = _register_group(machine.num_m_regs, source_span, 0, [])
        destination_base = _register_group(
            machine.num_m_regs,
            destination_span,
            16,
            [(source_base, source_base + source_span)],
        )
        return MixedFormatGeometry(source_base, destination_base, nsq)

    def _pairs(
        self, machine: "MachineConfig", destination_name: str | None = None
    ) -> tuple[tuple[DType, DType], ...]:
        """The format pairs this configuration can form."""

        available = self._available(machine)
        pairs = []
        for source_name, destination in MIXED_FORMAT_PAIRS:
            if source_name not in available or destination not in available:
                continue
            if destination_name is not None and destination != destination_name:
                continue
            pairs.append((available[source_name], available[destination]))
        return tuple(pairs)

    def fits(
        self, machine: "MachineConfig", instruction: "Instruction", dtype: DType | None
    ) -> bool:
        """Whether this destination format has one feasible source format."""

        if dtype is None:
            return False
        return any(
            self._payload(machine, source, destination) is not None
            for source, destination in self._pairs(machine, dtype.name)
        )

    def build(
        self,
        machine: "MachineConfig",
        instruction: "Instruction",
        dtype: DType | None,
    ) -> tuple[Case, ...]:
        if dtype is None:
            raise ValueError("a mixed-format case is always formed from a datatype")
        cases = [
            Case(
                number=0,
                dtype=dtype,
                payload=payload,
                description=payload.description,
            )
            for payload in (
                self._payload(machine, source, destination)
                for source, destination in self._pairs(machine, dtype.name)
            )
            if payload is not None
        ]
        return tuple(cases)

    def _payload(
        self,
        machine: "MachineConfig",
        source: "DType",
        destination: "DType",
    ) -> MixedFormatCase | None:
        """The encoded stimulus and answer of one pair, or ``None`` if unusable."""

        operation = self.operation
        geometry = self._geometry(machine, source.bits, destination.bits)
        count = geometry.nsq * machine.nelem
        sources: list[int] = []
        answers: list[int] = []
        for value in operation.stimulus:
            encoded = encode_exact(value, source.name)
            if encoded is None:
                continue
            if operation.answer_is_exact and encode_exact(value, destination.name) is None:
                # Keep an exact case exact for a model that converts the source
                # element into the destination format before it evaluates the
                # operation: the conversion has to be lossless, or the case
                # would be asserting one model's internal order.
                continue
            if operation.answer_is_exact:
                expected = encode_exact(operation.exact_answer(value), destination.name)
                if expected is None:
                    continue
                answers.append(expected)
            sources.append(encoded)
        if not sources or (operation.answer_is_exact and not answers):
            return None
        return MixedFormatCase(
            source_dtype=source.name,
            destination_dtype=destination.name,
            source_values=_cycles(tuple(sources), count),
            expected=_cycles(tuple(answers), count) if answers else (),
            flags=0 if operation.answer_is_exact else FFLAGS_NX,
            exact=operation.answer_is_exact,
            description=(
                f"{operation.value}: {dtype_stem(source.name)} -> "
                f"{dtype_stem(destination.name)}"
            ),
            geometry=geometry,
        )

    def render(
        self,
        machine: "MachineConfig",
        instruction: "Instruction",
        case: Case,
        out: CaseOutput,
    ) -> None:
        payload = case_payload(MixedFormatCase, case)
        source_format = FORMATS[payload.source_dtype]
        destination_format = FORMATS[payload.destination_dtype]
        geometry = payload.geometry
        stem = (
            f"mixed{case.number}_"
            f"{dtype_stem(payload.source_dtype)}_to_{dtype_stem(payload.destination_dtype)}"
        )
        source_label = f"{stem}_source"
        seed_label = f"{stem}_seed"
        destination_label = f"{stem}_destination"
        # One ``mls.rm``/``mss.rm`` moves exactly one formed square image: a
        # packed format carries ``pack`` logical squares per image, a wide one
        # carries a single square in ``nregs`` registers.  A pair whose source
        # and destination pack differently therefore needs one transfer per
        # image on the side that does not pack them, or the second logical
        # square would never leave memory.
        source_steps = _transfer_steps(
            machine,
            geometry.nsq,
            source_format.bits,
            geometry.source_base,
            source_label,
        )
        destination_steps = _transfer_steps(
            machine,
            geometry.nsq,
            destination_format.bits,
            geometry.destination_base,
            destination_label,
        )
        seed_steps = _transfer_steps(
            machine,
            geometry.nsq,
            destination_format.bits,
            geometry.destination_base,
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
                    f"    li      t0, {payload.destination_dtype}",
                    f"    msettyp m{register_base}, t0",
                    f"    la      t1, {label}",
                    f"    mls.rm     m{register_base}, t1",
                ]
            )
        out.text.append("    csrw    amefflags, x0")
        out.text.append(
            f"    {instruction.name} m{geometry.destination_base}, m{geometry.source_base}"
        )
        out.text.extend(
            [
                "    csrr    t5, amefflags",
                f"    EXPECT  t5, {payload.flags}",
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
        for index in _sampled_indices(len(payload.expected) or len(payload.source_values)):
            if payload.exact:
                out.text.extend(
                    check_dst_element_lines(
                        payload.expected[index],
                        destination_format.bits,
                        index,
                        destination_label,
                    )
                )
            else:
                out.text.extend(
                    _finite_element_lines(
                        index, destination_format.bits, payload.destination_dtype, destination_label
                    )
                )
        _emit_square(out, machine, source_label, payload.source_values, source_format.bits)
        _emit_square(
            out,
            machine,
            seed_label,
            (CANONICAL_NAN[payload.destination_dtype],) * len(payload.source_values),
            destination_format.bits,
        )
        # The approximate cases do not know the value, so the store target is a
        # scratch image; the exact cases seed it with the answer as well, which
        # keeps the expected image next to the case that checks it.
        _emit_square(
            out,
            machine,
            destination_label,
            payload.expected
            if payload.exact
            else (CANONICAL_NAN[payload.destination_dtype],) * len(payload.source_values),
            destination_format.bits,
        )
        out.data.append("")


def _transfer_steps(
    machine: "MachineConfig", nsq: int, element_bits: int, base: int, label: str
) -> list[tuple[int, str]]:
    """The register group and image label of every ``mls.rm``/``mss.rm`` step.

    One transfer moves one formed square image.  A packed format fits ``pack``
    logical squares in an image, so a packed operand needs fewer transfers than
    logical squares; a wide one needs exactly one per square.
    """

    pack = _pack_factor(machine, element_bits)
    if nsq % pack != 0:
        raise ValueError(f"{nsq} logical squares do not fill {pack}-square images")
    stride = machine.nregs(element_bits)
    return [
        (base + image * stride, label if image == 0 else f"{label}_block{image}")
        for image in range(nsq // pack)
    ]


def _sampled_indices(count: int) -> list[int]:
    """The element positions a mixed-format case checks."""

    return sorted({0, 1, 2, count - 1})


def _emit_square(
    out: CaseOutput,
    machine: "MachineConfig",
    label: str,
    values: tuple[int, ...],
    element_bits: int,
) -> None:
    """Emit one operand image, one physical square at a time."""

    per_block = machine.storage_elements(element_bits)
    if len(values) % per_block != 0:
        raise ValueError(
            f"{label}: {len(values)} elements do not fill {per_block}-element squares"
        )
    for block in range(len(values) // per_block):
        block_label = label if block == 0 else f"{label}_block{block}"
        out.data.extend(
            square_lines(
                block_label,
                values[block * per_block : (block + 1) * per_block],
                element_bits,
                machine,
            )
        )


def _finite_element_lines(
    index: int, element_bits: int, dtype_name: str, label: str
) -> list[str]:
    """Verify that one stored element is a finite number rather than a NaN."""

    width = element_bits // 8
    offset = index * width + width - 1
    limit = FINITE_LIMIT_BYTE[dtype_name]
    unique = f".Lfinite_{label}_{index}"
    return [
        f"    la      t3, {label}",
        *load_byte_lines("t4", "t3", offset),
        "    andi    t4, t4, 0x7f",
        f"    li      t6, {limit}",
        f"    bltu    t4, t6, {unique}",
        "    RVMODEL_HALT_FAIL",
        f"{unique}:",
        "",
    ]


__all__ = [
    "MIXED_FORMAT_PAIRS",
    "FloatFormat",
    "FloatMixedFormat",
    "MixedFormatCase",
    "MixedFormatGeometry",
    "encode_exact",
    "floor_log2",
]
