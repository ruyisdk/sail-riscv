#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Segment layout and byte expectations of the strided memory transfers.

A strided transfer walks *segments* of one square at a stride: a normal transfer
uses one element per segment, a transposed one uses one square column per
segment, and a packed (storage-only) transfer fills each segment with
``UDS / element_bits`` squares.  The address arithmetic is the whole test, so it
is computed here in one place and checked byte-for-byte by
``tests/test_strided_memory_parity.py``.
"""

from __future__ import annotations

from dataclasses import dataclass

from mmul_gen.asm import (
    data_element_lines,
    hex_value,
    load_byte_lines,
    pack_nibbles,
)
from mmul_gen.machine import MachineConfig

#: Byte the comparison images are filled with; a missing store leaves 0xa5.
FILL_BYTE = 0xA5


@dataclass(frozen=True)
class StridedTransfer:
    """Which direction one strided transfer moves data, and in what order."""

    is_load: bool
    transposed: bool


def normal_value(row: int, col: int, element_bits: int, n: int) -> int:
    """Element value of the row-major ramp every normal segment carries."""

    return (row * n + col + 1) & ((1 << element_bits) - 1)


def packed_value(square: int, row: int, col: int, element_bits: int) -> int:
    """Element value of one square inside a packed segment."""

    return (1 + square * 7 + row * 3 + col * 5) & ((1 << element_bits) - 1)


def segment_index(transfer: StridedTransfer, square: int, row: int, col: int, n: int) -> int:
    """Which segment of the destination one source element lands in."""

    return square * n + col if transfer.transposed else row


def segment_values(
    transfer: StridedTransfer,
    element_bits: int,
    uds: int,
    n: int,
    *,
    packed: bool = False,
) -> list[list[int]]:
    """The values of every segment, in the order the transfer lays them out."""

    pack_factor = max(1, uds // element_bits) if packed else 1
    segment_count = n if not transfer.transposed else pack_factor * n
    segments: list[list[int]] = [[] for _ in range(segment_count)]
    for square in range(pack_factor):
        for row in range(n):
            for col in range(n):
                segment = segment_index(transfer, square, row, col, n)
                value = (
                    packed_value(square, row, col, element_bits)
                    if packed
                    else normal_value(row, col, element_bits, n)
                )
                segments[segment].append(value)
    return segments


def element_bytes(value: int, element_bits: int) -> list[int]:
    """Little-endian byte image of one element."""

    return [(value >> (8 * offset)) & 0xFF for offset in range(element_bits // 8)]


def encoded_bytes(values: list[int], element_bits: int) -> list[int]:
    """Byte image of a value list, packing nibbles for four-bit elements."""

    if element_bits == 4:
        return pack_nibbles(values)
    return [byte for value in values for byte in element_bytes(value, element_bits)]


def byte_region_lines(
    label: str, segments: list[list[int]], stride: int, element_bits: int
) -> list[str]:
    """One strided source region: every segment, padded out to the stride."""

    lines = [f".balign {stride}", f"{label}:"]
    for values in segments:
        if element_bits == 4:
            packed = ", ".join(hex_value(value, 8) for value in pack_nibbles(values))
            lines.append(f"    .byte {packed}")
        else:
            lines.extend(data_element_lines(values, element_bits))
        padding = stride - len(encoded_bytes(values, element_bits))
        if padding:
            lines.extend([f"    .rept {padding}", f"    .byte {hex_value(FILL_BYTE, 8)}", "    .endr"])
    return lines


def byte_fill_region_lines(label: str, byte_count: int, alignment: int) -> list[str]:
    """A destination region pre-filled with the fill byte."""

    return [
        f".balign {alignment}",
        f"{label}:",
        f"    .rept {byte_count}",
        f"    .byte {hex_value(FILL_BYTE, 8)}",
        "    .endr",
    ]


def byte_expectation_lines(
    label: str, offsets_and_values: list[tuple[int, int]]
) -> list[str]:
    """Check individual bytes of one region against their expected values."""

    lines = [f"    la      t3, {label}"]
    for offset, value in offsets_and_values:
        lines.extend(load_byte_lines("t4", "t3", offset))
        lines.append(f"    EXPECT  t4, {hex_value(value, 8)}")
    return lines


def linear_square_lines(
    label: str, square: int, element_bits: int, machine: MachineConfig
) -> list[str]:
    """One packed square laid out linearly, as a segment source."""

    values = [
        packed_value(square, row, col, element_bits)
        for row in range(machine.n)
        for col in range(machine.n)
    ]
    lines = [
        f".balign {machine.square_bytes(element_bits)}",
        f"{label}:",
    ]
    if element_bits == 4:
        packed = ", ".join(hex_value(value, 8) for value in pack_nibbles(values))
        lines.append(f"    .byte {packed}")
        return lines
    lines.extend(data_element_lines(values, element_bits))
    return lines


def normal_linear_square_lines(
    label: str, element_bits: int, machine: MachineConfig
) -> list[str]:
    """One packed square laid out as the normal (row-major) ramp."""

    values = [
        normal_value(row, col, element_bits, machine.n)
        for row in range(machine.n)
        for col in range(machine.n)
    ]
    return [
        f".balign {machine.square_bytes(element_bits)}",
        f"{label}:",
        *data_element_lines(values, element_bits),
    ]


def packed_linear_values(element_bits: int, uds: int, n: int) -> list[int]:
    """Every packed square of one M image, concatenated."""

    return [
        packed_value(square, row, col, element_bits)
        for square in range(uds // element_bits)
        for row in range(n)
        for col in range(n)
    ]


def packed_linear_region_lines(
    label: str, element_bits: int, uds: int, n: int
) -> list[str]:
    """A packed linear image: one store slot per element, no stride padding."""

    byte_values = encoded_bytes(packed_linear_values(element_bits, uds, n), element_bits)
    packed = ", ".join(hex_value(value, 8) for value in byte_values)
    return [
        f".balign {len(byte_values)}",
        f"{label}:",
        f"    .byte {packed}",
    ]


def normal_load_case_lines(
    mnemonic: str,
    transfer: StridedTransfer,
    dtype_name: str,
    element_bits: int,
    stride_bytes: int,
    label_prefix: str,
    n: int,
) -> list[str]:
    """Load one whole square, one element per segment, then store it back.

    The readback is linear (stride-free), so it shows exactly which element the
    transfer put in which segment slot.
    """

    source_label = f"{label_prefix}normal_src"
    destination_label = f"{label_prefix}normal_dst"
    return [
        f"    # {mnemonic}: {element_bits}-bit unit segment layout",
        f"    li      t0, {dtype_name}",
        "    msettyp m0, t0",
        f"    la      t1, {source_label}",
        f"    li      t2, {stride_bytes}",
        f"    {mnemonic} m0, t1, t2",
        f"    la      t1, {destination_label}",
        "    mss.rm  m0, t1",
        *byte_expectation_lines(
            destination_label, normal_linear_expectations(element_bits, n)
        ),
    ]


def normal_store_case_lines(
    mnemonic: str,
    transfer: StridedTransfer,
    dtype_name: str,
    element_bits: int,
    stride_bytes: int,
    label_prefix: str,
    n: int,
) -> list[str]:
    """Store one square with a stride, then store it again with stride zero.

    The first store lays one element per segment; the second one is the overlap
    case, where every segment lands on the same address and the last element of
    the square is what survives.
    """

    source_label = f"{label_prefix}normal_src"
    destination_label = f"{label_prefix}normal_dst"
    overlap_label = f"{label_prefix}normal_overlap"
    return [
        f"    # {mnemonic}: {element_bits}-bit unit segment layout and overlapping segments",
        f"    li      t0, {dtype_name}",
        "    msettyp m0, t0",
        f"    la      t1, {source_label}",
        "    mls.rm  m0, t1",
        f"    la      t1, {destination_label}",
        f"    li      t2, {stride_bytes}",
        f"    {mnemonic} m0, t1, t2",
        *byte_expectation_lines(
            destination_label,
            normal_strided_expectations(transfer, element_bits, stride_bytes, n),
        ),
        f"    la      t1, {overlap_label}",
        "    li      t2, 0",
        f"    {mnemonic} m0, t1, t2",
        *byte_expectation_lines(
            overlap_label, overlap_expectations(transfer, element_bits, n)
        ),
    ]


def packed_load_case_lines(
    mnemonic: str,
    storage_dtype: str,
    compute_dtype: str,
    storage_bits: int,
    compute_bits: int,
    stride_bytes: int,
    label_prefix: str,
    is_signed: bool,
    n: int,
) -> list[str]:
    """Load a packed image, then widen it into two squares and store them back.

    Both destinations are checked against the packed ramp, one square each; the
    second register is only given its type, which is all its store needs.
    """

    source_label = f"{label_prefix}packed_src"
    square0_label = f"{label_prefix}packed_square0_dst"
    square1_label = f"{label_prefix}packed_square1_dst"
    return [
        f"    # {mnemonic}: packed {storage_bits}-bit segment layout",
        f"    li      t0, {storage_dtype}",
        "    msettyp m0, t0",
        f"    la      t1, {source_label}",
        f"    li      t2, {stride_bytes}",
        f"    {mnemonic} m0, t1, t2",
        f"    li      t0, {compute_dtype}",
        "    msettyp m2, t0",
        "    msettyp m3, t0",
        "    mconv.ew m2, m0",
        f"    la      t1, {square0_label}",
        "    mss.rm  m2, t1",
        f"    la      t1, {square1_label}",
        "    mss.rm  m3, t1",
        *byte_expectation_lines(
            square0_label,
            packed_linear_expectations(0, storage_bits, compute_bits, is_signed, n),
        ),
        *byte_expectation_lines(
            square1_label,
            packed_linear_expectations(1, storage_bits, compute_bits, is_signed, n),
        ),
    ]


def packed_storage_load_case_lines(
    mnemonic: str,
    dtype_name: str,
    storage_bits: int,
    uds: int,
    stride_bytes: int,
    label_prefix: str,
    n: int,
) -> list[str]:
    """Load a packed image with a stride, then store it back linearly.

    Nothing is converted: the readback shows that a strided load keeps every
    slot of the packed image exactly where the storage layout puts it.
    """

    source_label = f"{label_prefix}storage_src"
    destination_label = f"{label_prefix}storage_dst"
    return [
        f"    # {mnemonic}: bit-preserving packed storage for {dtype_name}",
        f"    li      t0, {dtype_name}",
        "    msettyp m0, t0",
        f"    la      t1, {source_label}",
        f"    li      t2, {stride_bytes}",
        f"    {mnemonic} m0, t1, t2",
        f"    la      t1, {destination_label}",
        "    mss.rm  m0, t1",
        *byte_expectation_lines(
            destination_label,
            list(
                enumerate(
                    encoded_bytes(
                        packed_linear_values(storage_bits, uds, n), storage_bits
                    )
                )
            ),
        ),
    ]


def packed_store_case_lines(
    mnemonic: str,
    transfer: StridedTransfer,
    storage_dtype: str,
    compute_dtype: str,
    storage_bits: int,
    compute_bits: int,
    stride_bytes: int,
    label_prefix: str,
    n: int,
) -> list[str]:
    """Narrow two computed squares into one packed image and store it strided."""

    square0_label = f"{label_prefix}packed_square0_src"
    square1_label = f"{label_prefix}packed_square1_src"
    destination_label = f"{label_prefix}packed_dst"
    return [
        f"    # {mnemonic}: packed {storage_bits}-bit segment layout",
        f"    li      t0, {compute_dtype}",
        "    msettyp m2, t0",
        "    msettyp m3, t0",
        f"    la      t1, {square0_label}",
        "    mls.rm  m2, t1",
        f"    la      t1, {square1_label}",
        "    mls.rm  m3, t1",
        f"    li      t0, {storage_dtype}",
        "    msettyp m0, t0",
        "    mconv.ew m0, m2",
        f"    la      t1, {destination_label}",
        f"    li      t2, {stride_bytes}",
        f"    {mnemonic} m0, t1, t2",
        *byte_expectation_lines(
            destination_label,
            packed_strided_expectations(
                transfer, storage_bits, compute_bits, stride_bytes, n
            ),
        ),
    ]


def packed_storage_store_case_lines(
    mnemonic: str,
    transfer: StridedTransfer,
    dtype_name: str,
    storage_bits: int,
    uds: int,
    stride_bytes: int,
    label_prefix: str,
    n: int,
) -> list[str]:
    """Store a packed image with a stride, converting nothing."""

    source_label = f"{label_prefix}storage_src"
    destination_label = f"{label_prefix}storage_dst"
    return [
        f"    # {mnemonic}: bit-preserving packed storage for {dtype_name}",
        f"    li      t0, {dtype_name}",
        "    msettyp m0, t0",
        f"    la      t1, {source_label}",
        "    mls.rm  m0, t1",
        f"    la      t1, {destination_label}",
        f"    li      t2, {stride_bytes}",
        f"    {mnemonic} m0, t1, t2",
        *byte_expectation_lines(
            destination_label,
            packed_strided_expectations(transfer, storage_bits, uds, stride_bytes, n),
        ),
    ]


def normal_linear_expectations(element_bits: int, n: int) -> list[tuple[int, int]]:
    """Byte expectations of a loaded normal square: the ramp, row-major."""

    expectations: list[tuple[int, int]] = []
    for row in range(n):
        for col in range(n):
            value = normal_value(row, col, element_bits, n)
            base = (row * n + col) * (element_bits // 8)
            expectations.extend(
                (base + offset, byte)
                for offset, byte in enumerate(element_bytes(value, element_bits))
            )
    return expectations


def normal_strided_expectations(
    transfer: StridedTransfer, element_bits: int, stride_bytes: int, n: int
) -> list[tuple[int, int]]:
    """Byte expectations of a stored normal square: one element per segment."""

    expectations: list[tuple[int, int]] = []
    element_size = element_bits // 8
    for row in range(n):
        for col in range(n):
            segment = segment_index(transfer, 0, row, col, n)
            element = row if transfer.transposed else col
            base = segment * stride_bytes + element * element_size
            value = normal_value(row, col, element_bits, n)
            expectations.extend(
                (base + offset, byte)
                for offset, byte in enumerate(element_bytes(value, element_bits))
            )
    return expectations


def packed_linear_expectations(
    square: int, storage_bits: int, compute_bits: int, is_signed: bool, n: int
) -> list[tuple[int, int]]:
    """Byte expectations of one packed square widened into a compute dtype."""

    expectations: list[tuple[int, int]] = []
    for row in range(n):
        for col in range(n):
            value = packed_value(square, row, col, storage_bits)
            if is_signed and value & (1 << (storage_bits - 1)):
                value -= 1 << storage_bits
            value &= (1 << compute_bits) - 1
            base = (row * n + col) * (compute_bits // 8)
            expectations.extend(
                (base + offset, byte)
                for offset, byte in enumerate(element_bytes(value, compute_bits))
            )
    return expectations


def packed_strided_expectations(
    transfer: StridedTransfer,
    storage_bits: int,
    uds: int,
    stride_bytes: int,
    n: int,
) -> list[tuple[int, int]]:
    """Byte expectations of a stored packed image: whole segments, bit-preserving."""

    expectations: list[tuple[int, int]] = []
    for segment, values in enumerate(
        segment_values(transfer, storage_bits, uds, n, packed=True)
    ):
        for byte_offset, value in enumerate(encoded_bytes(values, storage_bits)):
            expectations.append((segment * stride_bytes + byte_offset, value))
    return expectations


def overlap_expectations(
    transfer: StridedTransfer, element_bits: int, n: int
) -> list[tuple[int, int]]:
    """Byte expectations of a stride-zero store: one segment written repeatedly.

    A zero stride makes every segment land on the same address, so the last
    segment of the square wins; that is what these expectations describe.
    """

    values = (
        [normal_value(row, n - 1, element_bits, n) for row in range(n)]
        if transfer.transposed
        else [normal_value(n - 1, col, element_bits, n) for col in range(n)]
    )
    return list(enumerate(encoded_bytes(values, element_bits)))


__all__ = [
    "FILL_BYTE",
    "StridedTransfer",
    "byte_expectation_lines",
    "byte_fill_region_lines",
    "byte_region_lines",
    "element_bytes",
    "encoded_bytes",
    "linear_square_lines",
    "normal_linear_expectations",
    "normal_load_case_lines",
    "normal_store_case_lines",
    "normal_linear_square_lines",
    "normal_strided_expectations",
    "normal_value",
    "overlap_expectations",
    "packed_linear_expectations",
    "packed_linear_region_lines",
    "packed_linear_values",
    "packed_load_case_lines",
    "packed_storage_load_case_lines",
    "packed_storage_store_case_lines",
    "packed_store_case_lines",
    "packed_strided_expectations",
    "packed_value",
    "segment_index",
    "segment_values",
]
