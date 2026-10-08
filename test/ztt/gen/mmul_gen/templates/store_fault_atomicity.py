#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""A store that faults must commit none of its bytes.

Both store paths stage every destination byte before writing any of them, so a
store that raises a fault leaves the destination exactly as it found it.  The
recipe drives that with a fault the model cannot avoid:

* a strided store whose second segment lands on an address with no memory
  region behind it -- Spike throws ``trap_store_access_fault`` when
  ``addr_to_mem`` returns null, and the Sail model fails the PMA check in
  ``phys_access_check``;
* a contiguous store whose second 16-byte window is pinned by a locked NAPOT
  PMP entry, which M-mode cannot bypass.

Both cases pre-fill the destination with ``0xa5`` and then check the bytes the
store would have written first.  A byte-at-a-time store leaves those bytes dirty
before it traps, so the check is what separates a staged write from an
incremental one.  A second case stores twice into the same window and checks
that the later store wins.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from mmul_gen.asm import check_bytes_lines, repeated_square_lines
from mmul_gen.machine import INTEGER, MachineConfig
from mmul_gen.templates.base import Case, CaseOutput, Template, case_payload

if TYPE_CHECKING:
    from mmul_gen.instruction import Instruction
    from mmul_gen.machine import DType

#: The descriptor every store case uses: a whole-register width at UDS 8, so the
#: store moves exactly one square of bytes and the raw and typed forms agree.
ELEMENT_DTYPE = "AME_UINT8_DTYPE"
ELEMENT_BITS = 8
#: The one UDS whose store geometry this recipe is written for.
STORE_UDS = 8
#: Byte no store wrote, so a partial write is visible.
UNTOUCHED_BYTE = 0xA5
#: Byte pattern the faulting store would commit if it were allowed to.
STORE_BYTE = 0x5A
#: The two images of the later-wins overlap case.
FIRST_IMAGE_BYTE = 0x11
SECOND_IMAGE_BYTE = 0x22
#: An address in no memory region of either model: the boot ROM ends at 0x2000
#: (Sail) and RAM starts at 0x8000_0000, so a store here has no backing memory.
NON_RAM_HOLE = 0x10000
#: Offset of the denied NAPOT region inside one contiguous store window.
DENIED_REGION_OFFSET = 16
#: mcause of a store/AMO access fault.
STORE_ACCESS_FAULT_CAUSE = 7
#: pmpcfg0 with entry 0 locked (L=1), A=NAPOT, and no R/W/X permission.
LOCKED_NAPOT_CFG = 0x98


@dataclass(frozen=True)
class StoreForm:
    """Which store shape one instruction uses."""

    #: Assembler-safe stem used in this form's labels.
    stem: str
    #: Whether the store takes a stride and moves one segment per row/column.
    strided: bool


@dataclass(frozen=True)
class StoreCase:
    """One case of the store-atomicity recipe."""

    #: ``True`` for the later-wins overlap case, ``False`` for the fault case.
    overlap: bool


def store_bytes(machine: MachineConfig) -> int:
    """Bytes one whole-square store moves.

    At UDS 8 the raw, row/column-major, and strided forms all move exactly one
    square, so one length serves every form.
    """

    return machine.nelem * machine.uds // 8


def store_lines(
    mnemonic: str,
    form: StoreForm,
    machine: MachineConfig,
    mreg: str,
    addr_reg: str,
    stride_reg: str,
) -> list[str]:
    """Emit one store of ``mreg`` to ``addr_reg``, with a stride when required."""

    if form.strided:
        return [
            f"    li      {stride_reg}, {machine.n}",
            f"    {mnemonic} {mreg}, {addr_reg}, {stride_reg}",
        ]
    return [f"    {mnemonic} {mreg}, {addr_reg}"]


def fill_region_lines(label: str, byte_count: int) -> list[str]:
    """A labelled destination region pre-filled with the untouched byte."""

    return [
        f".balign {byte_count}",
        f"{label}:",
        f"    .rept {byte_count}",
        f"    .byte {UNTOUCHED_BYTE:#x}",
        "    .endr",
    ]


class StoreFaultAtomicity(Template):
    """A store that raises an access fault commits none of its bytes."""

    name = "store_fault_atomicity"
    dtypes = INTEGER

    def __init__(self, form: StoreForm) -> None:
        """``form`` is the store shape the holding instruction uses."""

        self.form = form

    def fits(
        self,
        machine: MachineConfig,
        instruction: Instruction,
        dtype: DType | None = None,
    ) -> bool:
        return (
            dtype is not None
            and dtype.name == ELEMENT_DTYPE
            and machine.uds == STORE_UDS
        )

    def build(
        self, machine: MachineConfig, instruction: Instruction, dtype: DType | None
    ) -> Sequence[Case]:
        cases = [Case(number=0, dtype=dtype, payload=StoreCase(overlap=True))]
        if self._fault_is_reachable(machine):
            cases.append(Case(number=0, dtype=dtype, payload=StoreCase(overlap=False)))
        return cases

    def _fault_is_reachable(self, machine: MachineConfig) -> bool:
        """Whether the trigger lands inside this form's store extent.

        A strided store always reaches its second segment.  A contiguous store
        reaches the denied PMP region only when it is longer than that region.
        """

        if self.form.strided:
            return True
        return store_bytes(machine) > DENIED_REGION_OFFSET

    def checked_bytes(self, machine: MachineConfig) -> int:
        """How many leading bytes of the window the fault case verifies."""

        if self.form.strided:
            return machine.n
        return DENIED_REGION_OFFSET

    def render(
        self,
        machine: MachineConfig,
        instruction: Instruction,
        case: Case,
        out: CaseOutput,
    ) -> None:
        payload = case_payload(StoreCase, case)
        prefix = f"case{case.number}_{self.form.stem}_"
        if payload.overlap:
            self._render_overlap(machine, instruction, prefix, out)
        else:
            self._render_fault(machine, instruction, prefix, out)

    def _render_overlap(
        self,
        machine: MachineConfig,
        instruction: Instruction,
        prefix: str,
        out: CaseOutput,
    ) -> None:
        size = store_bytes(machine)
        first_source = f"{prefix}overlap_first_src"
        second_source = f"{prefix}overlap_second_src"
        window = f"{prefix}overlap_dst"
        out.text.extend(
            [
                "    # overlapping stores: the later store wins",
                f"    li      t0, {ELEMENT_DTYPE}",
                "    msettyp m0, t0",
                "    msettyp m1, t0",
                f"    la      t1, {first_source}",
                "    mls.rm  m0, t1",
                f"    la      t1, {second_source}",
                "    mls.rm  m1, t1",
                f"    la      t2, {window}",
            ]
        )
        out.text.extend(
            store_lines(instruction.name, self.form, machine, "m0", "t2", "t3")
        )
        out.text.extend(
            store_lines(instruction.name, self.form, machine, "m1", "t2", "t3")
        )
        out.text.extend(
            check_bytes_lines(window, [SECOND_IMAGE_BYTE] * size, (0, size - 1))
        )
        out.data.extend(
            repeated_square_lines(first_source, FIRST_IMAGE_BYTE, ELEMENT_BITS, machine)
        )
        out.data.extend(
            repeated_square_lines(
                second_source, SECOND_IMAGE_BYTE, ELEMENT_BITS, machine
            )
        )
        out.data.extend(fill_region_lines(window, size))
        out.data.append("")

    def _render_fault(
        self,
        machine: MachineConfig,
        instruction: Instruction,
        prefix: str,
        out: CaseOutput,
    ) -> None:
        size = store_bytes(machine)
        source = f"{prefix}fault_src"
        window = f"{prefix}fault_dst"
        out.text.extend(
            [
                "    # a store that faults must commit no byte",
                f"    li      t0, {ELEMENT_DTYPE}",
                "    msettyp m0, t0",
                f"    la      t1, {source}",
                "    mls.rm  m0, t1",
                "    TRAP_GUARD_ARM",
                f"    TRAP_GUARD_ACCEPT_CAUSE {STORE_ACCESS_FAULT_CAUSE}",
            ]
        )
        out.text.extend(self._fault_trigger_lines(instruction.name, window))
        out.text.append(f"    EXPECT_TRAP_CAUSE 1, {STORE_ACCESS_FAULT_CAUSE}")
        out.text.extend(
            check_bytes_lines(
                window,
                [UNTOUCHED_BYTE] * size,
                tuple(range(self.checked_bytes(machine))),
            )
        )
        out.data.extend(repeated_square_lines(source, STORE_BYTE, ELEMENT_BITS, machine))
        out.data.extend(fill_region_lines(window, size))
        out.data.append("")

    def _fault_trigger_lines(self, mnemonic: str, window: str) -> list[str]:
        """Set up the fault, then issue the store that must not commit."""

        if self.form.strided:
            return [
                f"    la      t1, {window}",
                f"    li      t2, {NON_RAM_HOLE}",
                "    sub     t2, t2, t1",
                f"    {mnemonic} m0, t1, t2",
            ]
        return [
            f"    la      t0, {window}",
            f"    addi    t0, t0, {DENIED_REGION_OFFSET}",
            "    srli    t0, t0, 2",
            "    ori     t0, t0, 1",
            "    csrw    pmpaddr0, t0",
            f"    li      t0, {LOCKED_NAPOT_CFG:#x}",
            "    csrw    pmpcfg0, t0",
            f"    la      t1, {window}",
            f"    {mnemonic} m0, t1",
        ]


__all__ = [
    "DENIED_REGION_OFFSET",
    "ELEMENT_DTYPE",
    "LOCKED_NAPOT_CFG",
    "NON_RAM_HOLE",
    "STORE_ACCESS_FAULT_CAUSE",
    "StoreCase",
    "StoreFaultAtomicity",
    "StoreForm",
    "store_bytes",
    "store_lines",
]
