#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Shared shape and byte layout of the indexed packed-slot templates.

``mpack.ew.x`` and ``munpack.ew.x`` are the two directions of one conversion
between a descriptor stored at half the active UDS and its same-signedness twin
at the full UDS.  Both run the same three input patterns over the same packed
descriptor pairs, lay their images out identically, and differ only in the
direction they convert, so the pair relation, the input patterns, and the image
helpers live here while the two renderers own one instruction each.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from mmul_gen.asm import (
    check_bytes_lines,
    check_dst_element_lines,
    data_element_lines,
    hex_value,
    pack_nibbles,
)
from mmul_gen.case_description import description
from mmul_gen.machine import (
    DType,
    MachineConfig,
    PACKED_CONVERSION,
    dtype_is_signed_int,
)
from mmul_gen.reference import packed_compute_dtype
from mmul_gen.templates.base import Case, Template

if TYPE_CHECKING:
    from mmul_gen.instruction import Instruction


#: Storage slot every packed-slot case addresses.
SLOT = 3
#: The input patterns every packed-slot instruction runs, in case order.
INPUT_CASES = ("selected_slot", "preserved_slot", "signed_boundary_values")
#: Fill byte of a destination region no store wrote.
UNTOUCHED_BYTE = 0xA5


@dataclass(frozen=True)
class PackedSlotPayload:
    """One packed-storage/compute pair and the input pattern under test."""

    storage_dtype: str
    compute_dtype: str
    is_signed: bool
    input_case: str


def encoded_values(values: Sequence[int], element_bits: int) -> list[int]:
    """Physical byte image of ``values``: nibble-packed at 4 bits, else bytewise."""

    if element_bits == 4:
        return pack_nibbles(values)
    return [
        (value >> (8 * byte_offset)) & 0xFF
        for value in values
        for byte_offset in range(element_bits // 8)
    ]


def data_lines(
    label: str,
    values: Sequence[int],
    element_bits: int,
    machine: MachineConfig,
) -> list[str]:
    """One labelled square image, aligned to the square the dtype forms.

    A nibble-quantised image is emitted one packed byte per line; a wider one
    keeps the shared packed-operand-list form, which is an emission choice
    rather than a rounding difference.
    """

    lines = [
        f".balign {machine.square_bytes(element_bits)}",
        f"{label}:",
    ]
    if element_bits == 4:
        lines.extend(
            f"    .byte {hex_value(value, 8)}"
            for value in encoded_values(values, element_bits)
        )
    else:
        lines.extend(data_element_lines(values, element_bits))
    return lines


def destination_lines(label: str, element_bits: int, machine: MachineConfig) -> list[str]:
    """One labelled square prefilled with the untouched byte."""

    square_bytes = machine.square_bytes(element_bits)
    return [
        f".balign {square_bytes}",
        f"{label}:",
        f"    .rept {square_bytes}",
        f"    .byte {hex_value(UNTOUCHED_BYTE, 8)}",
        "    .endr",
    ]


def preserved_slot(case_number: int, element_bits: int, nelem: int) -> list[int]:
    """The slot values a case leaves untouched, walking down from the top."""

    mask = (1 << element_bits) - 1
    return [(mask - index - case_number) & mask for index in range(nelem)]


def boundary_values(case_number: int, element_bits: int, nelem: int) -> list[int]:
    """A rotating sweep of the all-zero, one, and both signed edges."""

    mask = (1 << element_bits) - 1
    pattern = [
        0,
        1,
        2,
        (1 << (element_bits - 1)) - 1,
        1 << (element_bits - 1),
        mask - 1,
        mask,
    ]
    return [
        pattern[(index + case_number) % len(pattern)] & mask for index in range(nelem)
    ]


def case_source_values(
    case_number: int,
    element_bits: int,
    nelem: int,
    input_case: str,
) -> list[int]:
    """The values one input pattern feeds a case."""

    mask = (1 << element_bits) - 1
    if input_case == "selected_slot":
        return [(index + 1 + case_number) & mask for index in range(nelem)]
    if input_case == "preserved_slot":
        return [((index * 3) + 5 + case_number) & mask for index in range(nelem)]
    if input_case == "signed_boundary_values":
        return boundary_values(case_number, element_bits, nelem)
    raise ValueError(f"unsupported pack input case: {input_case}")


def byte_check_lines(label: str, expected: Sequence[int]) -> list[str]:
    """Check the low, middle, and high bytes of a stored packed image."""

    offsets = [0, 1, 2, len(expected) // 2 - 1, len(expected) // 2, len(expected) - 2, len(expected) - 1]
    return check_bytes_lines(label, expected, sorted(set(offsets)))


def element_check_lines(
    label: str, expected: Sequence[int], element_bits: int, nelem: int
) -> list[str]:
    """Check the low, middle, and high elements of a stored compute square."""

    lines: list[str] = []
    for index in (0, 1, 2, 7, 8, nelem - 1):
        lines.extend(check_dst_element_lines(expected[index], element_bits, index, label))
    return lines


class PackedSlotConversion(Template, family_base=True):
    """One direction of the indexed packed-slot conversion."""

    dtypes = PACKED_CONVERSION

    def build(
        self, machine: MachineConfig, instruction: Instruction, dtype: DType
    ) -> Sequence[Case]:
        return [
            Case(
                number=0,
                dtype=dtype,
                payload=PackedSlotPayload(
                    storage_dtype=dtype.name,
                    compute_dtype=packed_compute_dtype(dtype.name, machine.uds),
                    is_signed=dtype_is_signed_int(dtype.name),
                    input_case=input_case,
                ),
                description=description(input_case),
            )
            for input_case in INPUT_CASES
        ]


__all__ = [
    "INPUT_CASES",
    "SLOT",
    "UNTOUCHED_BYTE",
    "PackedSlotConversion",
    "PackedSlotPayload",
    "boundary_values",
    "byte_check_lines",
    "case_source_values",
    "data_lines",
    "destination_lines",
    "element_check_lines",
    "encoded_values",
    "preserved_slot",
]
