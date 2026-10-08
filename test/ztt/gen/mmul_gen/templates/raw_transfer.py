#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Raw physical-register transfer: one M register moves as an opaque byte image.

``mls.1r``/``mss.1r`` move exactly one physical M register -- ``nelem * uds / 8``
bytes -- and never consult the descriptor.  So the descriptor only decides which
encoding the assembler accepts: the byte image, the register edge, and the
sentinel register are the same for every descriptor, and both mnemonics are
exercised inside one case (load to seed, store to read back).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from mmul_gen.asm import data_element_lines, load_byte_lines
from mmul_gen.case_description import description
from mmul_gen.machine import EVERY_DTYPE, MachineConfig, dtype_stem
from mmul_gen.templates.base import Case, CaseOutput, Template

if TYPE_CHECKING:
    from mmul_gen.instruction import Instruction
    from mmul_gen.machine import DType


#: Load one physical M register from memory.
RAW_LOAD_MNEMONIC = "mls.1r"
#: Store one physical M register to memory.
RAW_STORE_MNEMONIC = "mss.1r"
#: Byte filling every destination region, so a byte the transfer did not write
#: is still recognisable as untouched.
UNTOUCHED_BYTE = 0xA5


def physical_register_bytes(machine: MachineConfig) -> int:
    """Bytes in one physical M register: an N x N square of UDS-sized units."""

    return machine.nelem * machine.uds // 8


def check_offsets(machine: MachineConfig) -> tuple[int, ...]:
    """Offsets inspected inside a transferred image: both edges and the middle."""

    size = physical_register_bytes(machine)
    return (0, 1, size // 2 - 1, size - 2, size - 1)


def image_bytes(seed: int, step: int, case_number: int, size: int) -> list[int]:
    """Deterministic byte image, so every check has a known expected value."""

    return [(seed + case_number + byte * step) & 0xFF for byte in range(size)]


def check_lines(label: str, expected: list[int], offsets: Sequence[int]) -> list[str]:
    """Load one byte at each offset and compare it with the expected image."""

    lines = [f"    la      t3, {label}"]
    for offset in offsets:
        lines.extend(
            [
                *load_byte_lines("t4", "t3", offset),
                f"    EXPECT  t4, {expected[offset]}",
            ]
        )
    lines.append("")
    return lines


def data_lines(label: str, values: Sequence[int], machine: MachineConfig) -> list[str]:
    """One labelled byte image, aligned to a whole physical register."""

    return [
        f".balign {physical_register_bytes(machine)}",
        f"{label}:",
        *data_element_lines(values, 8),
    ]


def fill_lines(label: str, byte_count: int, machine: MachineConfig) -> list[str]:
    """One labelled region of sentinel bytes of an exact size."""

    return [
        f".balign {physical_register_bytes(machine)}",
        f"{label}:",
        f"    .rept {byte_count}",
        f"    .byte {UNTOUCHED_BYTE:#x}",
        "    .endr",
    ]


class RawTransfer(Template):
    """A fixed-size transfer reproduces its byte image for every descriptor."""

    name = "physical_image_and_register_edge"
    dtypes = EVERY_DTYPE

    def build(
        self, machine: MachineConfig, instruction: Instruction, dtype: DType
    ) -> Sequence[Case]:
        # The whole transfer block carries one label, ahead of the first
        # descriptor, so only the first case carries it.
        first = self.dtypes(machine)[0]
        return [
            Case(
                number=0,
                dtype=dtype,
                description=description(self.name) if dtype == first else None,
            )
        ]

    def render(
        self,
        machine: MachineConfig,
        instruction: Instruction,
        case: Case,
        out: CaseOutput,
    ) -> None:
        size = physical_register_bytes(machine)
        prefix = f"case{case.number}_{dtype_stem(case.dtype.name)}_"
        source_label = f"{prefix}source"
        sentinel_label = f"{prefix}sentinel_source"
        destination = f"{prefix}destination"
        sentinel_destination = f"{prefix}sentinel_destination"
        source = image_bytes(0x11, 3, case.number, size)
        sentinel = image_bytes(0x80, 5, case.number, size)

        out.text.extend(
            [
                f"    # case {case.number}: {instruction.name} fixed-size raw "
                f"transfer with {case.dtype.name}",
                f"    li      t0, {case.dtype.name}",
                "    msettyp m0, t0",
                # m1 has no descriptor after only m0 is configured.  A raw
                # transfer must still work, and m0's wide group must not
                # consume m1.
                f"    la      t1, {sentinel_label}",
                f"    {RAW_LOAD_MNEMONIC:<8} m1, t1",
                f"    la      t1, {source_label}",
                f"    {RAW_LOAD_MNEMONIC:<8} m0, t1",
                f"    la      t2, {destination}",
                f"    {RAW_STORE_MNEMONIC:<8} m0, t2",
                f"    la      t2, {sentinel_destination}",
                f"    {RAW_STORE_MNEMONIC:<8} m1, t2",
            ]
        )
        out.text.extend(check_lines(destination, source, check_offsets(machine)))
        # The byte directly past a physical M register proves that the store
        # did not transfer a descriptor-sized register group.
        out.text.extend(
            check_lines(destination, [*source, UNTOUCHED_BYTE], (size,))
        )
        out.text.extend(check_lines(sentinel_destination, sentinel, check_offsets(machine)))

        out.data.extend(data_lines(source_label, source, machine))
        out.data.extend(data_lines(sentinel_label, sentinel, machine))
        out.data.extend(fill_lines(destination, size + 1, machine))
        out.data.extend(fill_lines(sentinel_destination, size, machine))
        out.data.append("")


__all__ = ["RawTransfer", "physical_register_bytes"]


RAW_TRANSFER = RawTransfer()
