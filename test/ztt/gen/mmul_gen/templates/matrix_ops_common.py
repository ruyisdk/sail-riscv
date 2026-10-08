#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Stimulus and expectations of the matrix permute/reduce family.

Three operation shapes share this module because they share their stimulus: a
linear ramp ``1..nelem`` in the first source, a second ramp starting clear of it
in the second source, and -- for the indexed operations -- a table whose entries
are reduced modulo the active length by the hardware.

Expected values are computed here from the *declared* semantics of each
instruction (its axis and its aggregate), so one template covers every
instruction of a group and a new instruction only declares what it does.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from mmul_gen.asm import data_element_lines
from mmul_gen.inputs import gather_scatter_index_values, sequence_values
from mmul_gen.machine import MachineConfig, dtype_is_signed_int

if TYPE_CHECKING:
    from mmul_gen.instructions.matrix_ops.base import MatrixAxis, Reduction, ScatterAccess
    from mmul_gen.machine import DType


#: The second source ramp starts here so a value names its own source square.
SECOND_SOURCE_OFFSET = 101
#: Byte alignment of the packed index tables.
INDEX_TABLE_ALIGNMENT = 64
#: Destination pre-fill, so a partial write cannot pass a check.
DESTINATION_FILL = 0xA5


def values_a(machine: MachineConfig) -> list[int]:
    """First source square: the linear ramp ``1..nelem``."""

    return sequence_values(machine.nelem)


def values_b(machine: MachineConfig) -> list[int]:
    """Second source square, offset so it cannot be confused with the first."""

    return sequence_values(machine.nelem, SECOND_SOURCE_OFFSET)


def interpreted_values(
    values: Sequence[int], element_bits: int, signed: bool
) -> list[int]:
    """The values as the model reinterprets them through the active datatype.

    The stimulus is truncated to the element width when it reaches memory, so an
    expectation for a non-linear operation has to wrap the same way: past the
    element width ``256`` reads back as ``0`` in a UINT8 square.
    """

    mask = (1 << element_bits) - 1
    interpreted = [value & mask for value in values]
    if signed:
        sign_bit = 1 << (element_bits - 1)
        interpreted = [
            value - (1 << element_bits) if value & sign_bit else value
            for value in interpreted
        ]
    return interpreted


def source_data_lines(
    label: str, values: Sequence[int], element_bits: int, machine: MachineConfig
) -> list[str]:
    """One labelled square of element values."""

    return [
        f".balign {machine.square_bytes(element_bits)}",
        f"{label}:",
        *data_element_lines(values, element_bits),
    ]


def byte_index_data_lines(label: str, values: Sequence[int]) -> list[str]:
    """One labelled square of byte-sized index values."""

    return [
        f".balign {INDEX_TABLE_ALIGNMENT}",
        f"{label}:",
        *data_element_lines(values, 8),
    ]


def destination_lines(label: str, element_bits: int, machine: MachineConfig) -> list[str]:
    """A touched square, pre-filled so a partial write cannot pass."""

    square_bytes = machine.square_bytes(element_bits)
    return [
        f".balign {square_bytes}",
        f"{label}:",
        f"    .rept {square_bytes}",
        f"    .byte {DESTINATION_FILL:#04x}",
        "    .endr",
    ]


def extra_registers(
    machine: MachineConfig, element_bits: int
) -> tuple[int, int, int, int, int]:
    """Register bases of an operation that needs three disjoint groups.

    Returns the first source, second source, destination, destination pair, and
    index groups.  The index group is the last register of the file, so it never
    overlaps a source or destination group.
    """

    nregs = machine.nregs(element_bits)
    src_a_reg = 0
    src_b_reg = nregs
    dest_reg = 2 * nregs
    if dest_reg + nregs > machine.num_m_regs:
        raise ValueError(
            f"three groups of {nregs} M registers do not fit element_bits="
            f"{element_bits}, uds={machine.uds} in a {machine.num_m_regs} register file"
        )
    return src_a_reg, src_b_reg, dest_reg, dest_reg + nregs, machine.num_m_regs - 1


def reduce_expected(
    machine: MachineConfig,
    dtype: DType,
    axis: "MatrixAxis",
    reduction: "Reduction",
    prefix: bool,
) -> list[tuple[int, int]]:
    """The sampled elements and their expected values for one reduce case."""

    n = machine.n
    values = interpreted_values(
        values_a(machine), dtype.bits, dtype_is_signed_int(dtype.name)
    )
    indices = (
        axis.prefix_check_indices(n) if prefix else axis.reduce_check_indices(n)
    )
    checks = []
    for index in indices:
        row, col = divmod(index, n)
        members = (
            axis.prefix_indices(n, row, col) if prefix else axis.line_indices(n, row, col)
        )
        checks.append((index, reduction.aggregate([values[i] for i in members])))
    return checks


def max_value(dtype: DType) -> int:
    """The largest value the datatype can hold."""

    from mmul_gen.inputs import int_edge_value

    return int_edge_value(dtype.name, dtype.bits, "upper_bound")


def gather_expected(
    machine: MachineConfig, axis: "MatrixAxis", dtype: DType
) -> list[int]:
    """Expected square of an indexed read from the ramp source."""

    n = machine.n
    indices = gather_scatter_index_values(dtype.bits, n)
    source = values_a(machine)
    return [
        source[axis.source_index(n, indices[row * n + col] % n, row, col)]
        for row in range(n)
        for col in range(n)
    ]


def scatter_expected(
    machine: MachineConfig,
    axis: "MatrixAxis",
    access: "ScatterAccess",
    dtype: DType,
    initial: int,
) -> list[int]:
    """Expected square of an indexed accumulate over a seeded destination."""

    n = machine.n
    indices = gather_scatter_index_values(dtype.bits, n)
    source = interpreted_values(
        values_a(machine), dtype.bits, dtype_is_signed_int(dtype.name)
    )
    destination = [initial] * machine.nelem
    for row in range(n):
        for col in range(n):
            position = row * n + col
            target = axis.result_index(n, row, col, indices[position] % n)
            destination[target] = access.combine(destination[target], source[position])
    return destination


__all__ = [
    "DESTINATION_FILL",
    "INDEX_TABLE_ALIGNMENT",
    "SECOND_SOURCE_OFFSET",
    "byte_index_data_lines",
    "destination_lines",
    "extra_registers",
    "gather_expected",
    "interpreted_values",
    "max_value",
    "reduce_expected",
    "scatter_expected",
    "source_data_lines",
    "values_a",
    "values_b",
]
