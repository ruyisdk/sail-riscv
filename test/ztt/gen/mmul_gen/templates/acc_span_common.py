#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Value recipes shared by the two packed accumulator-span recipes.

A packed (storage-only) datatype makes one M register hold
``pack_factor = UDS / element_bits`` squares, so a single transfer moves a whole
*span* of accumulators.  The recipes here are what makes each square in that
span distinguishable in the read-back: every square gets its own value, and the
poison/corrupt pair is what proves that a rejected transfer wrote nothing.
"""

from __future__ import annotations

DOC_ZH = """\
两个打包累加器跨度配方共享的取值配方。

打包（仅存储）datatype 使一个 M 寄存器容纳 ``pack_factor = UDS / element_bits`` 个方阵，因此一次搬运会移动整段累加器跨度。这里的配方让该跨度中的每个方阵在读回时可区分：每个方阵都有各自的取值，而 poison/corrupt 这一对用来证明被拒绝的搬运没有写入任何内容。
"""

from collections.abc import Sequence

from mmul_gen.asm import check_dst_element_lines, repeated_square_lines
from mmul_gen.machine import MachineConfig

#: Value a rejected transfer must leave behind, and the image that would prove it
#: landed.  Four-bit elements get their own pair so the value stays a single
#: nibble.
POISON_VALUE = 0x5A
POISON_VALUE_4BIT = 0x0A
CORRUPT_VALUE = 0x3C
CORRUPT_VALUE_4BIT = 0x03


def packed_pack_factor(machine: MachineConfig, element_bits: int) -> int:
    """Squares held by one M register of this datatype."""

    return machine.uds // element_bits


def poison_value(element_bits: int) -> int:
    return POISON_VALUE_4BIT if element_bits == 4 else POISON_VALUE


def corrupt_value(element_bits: int) -> int:
    return CORRUPT_VALUE_4BIT if element_bits == 4 else CORRUPT_VALUE


def span_a_value(square: int, element_bits: int) -> int:
    """First-image value of one square in the span."""

    return square + 1 if element_bits == 4 else 0x11 * square + 0x03


def span_b_value(square: int, element_bits: int, pack_factor: int) -> int:
    """Second-image value of one square, distinct from the first image.

    Four-bit elements have to stay distinguishable inside one nibble across all
    ``pack_factor`` squares, so the offset is chosen to clear the first image.
    """

    if element_bits != 4:
        return 0x22 * square + 0x07
    offset = pack_factor + 1 if 2 * pack_factor + 1 <= 15 else pack_factor
    return square + offset


def flat_square(square_values: Sequence[int], element_count: int) -> list[int]:
    """One element value per square, repeated to fill a whole square."""

    return [
        value
        for square_value in square_values
        for _ in range(element_count)
        for value in [square_value]
    ]


def square_checks(
    square_values: Sequence[int],
    element_bits: int,
    machine: MachineConfig,
    label: str,
) -> list[str]:
    """Check the first and last element of every square in one read-back."""

    lines: list[str] = []
    for square, value in enumerate(square_values):
        first = square * machine.nelem
        lines.extend(check_dst_element_lines(value, element_bits, first, label))
        lines.extend(
            check_dst_element_lines(
                value, element_bits, first + machine.nelem - 1, label
            )
        )
    return lines


def uniform_image(
    label: str, value: int, element_bits: int, machine: MachineConfig
) -> list[str]:
    """One uniform square plus the blank line that closes it."""

    return [*repeated_square_lines(label, value, element_bits, machine), ""]


__all__ = [
    "CORRUPT_VALUE",
    "CORRUPT_VALUE_4BIT",
    "POISON_VALUE",
    "POISON_VALUE_4BIT",
    "corrupt_value",
    "flat_square",
    "packed_pack_factor",
    "poison_value",
    "span_a_value",
    "span_b_value",
    "square_checks",
    "uniform_image",
]
