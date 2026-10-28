#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""A memory transfer that faults commits nothing of the transfer it was asked for.

Spec:    programming_model.adoc:417-428 (§2.6.3)
Quote:   No partial completion is permitted: the faulting instruction commits no update to its destination `M` register group and performs no explicit data-memory write, neither to the faulting portion of the access nor to any other portion.
Checks:  a faulting store must leave every byte of its destination window at its pre-fill value, a faulting load must leave every byte of its destination M register group at its pre-fill value, and a later store into the same window must win

Every memory instruction stages its transfer before committing any of it, so a
transfer that raises a fault leaves both halves -- the destination `M` register
group and data memory -- exactly as it found them.  The recipe drives that with
faults the model cannot avoid:

* a strided transfer whose second segment lands on an address with no memory
  region behind it -- Spike throws the access fault when ``addr_to_mem`` returns
  null, and the Sail model fails the PMA check in ``phys_access_check``;
* a contiguous transfer whose second 16-byte window is pinned by a locked NAPOT
  PMP entry, which M-mode cannot bypass.

A store case pre-fills its window with ``0xa5`` and checks the bytes the store
would have written first; a load case pre-fills the destination group with
``0xa5``, faults, and copies the group out, so a load that filled its group
element by element before trapping is visible.  The store recipe also carries an
overlap case: two stores into one window, where the later store wins.
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

#: The descriptor every transfer case uses: a whole-register width at UDS 8, so
#: the transfer moves exactly one square of bytes and every form agrees.
ELEMENT_DTYPE = "AME_UINT8_DTYPE"
ELEMENT_BITS = 8
#: The one UDS whose transfer geometry this recipe is written for.
TRANSFER_UDS = 8
#: Load and store one physical M register, used to stage and to read back the
#: destination group of a load case.
RAW_LOAD_MNEMONIC = "mls.1r"
RAW_STORE_MNEMONIC = "mss.1r"
#: Byte no transfer wrote, so a partial write is visible.
UNTOUCHED_BYTE = 0xA5
#: Byte pattern the faulting transfer would commit if it were allowed to.
TRANSFER_BYTE = 0x5A
#: The two images of the later-wins overlap case.
FIRST_IMAGE_BYTE = 0x11
SECOND_IMAGE_BYTE = 0x22
#: An address in no memory region of either model: the boot ROM ends at 0x2000
#: (Sail) and RAM starts at 0x8000_0000, so a transfer here has no backing memory.
NON_RAM_HOLE = 0x10000
#: Offset of the denied NAPOT region inside one contiguous transfer window.
DENIED_REGION_OFFSET = 16
#: mcause of a load access fault.
LOAD_ACCESS_FAULT_CAUSE = 5
#: mcause of a store/AMO access fault.
STORE_ACCESS_FAULT_CAUSE = 7
#: pmpcfg0 with entry 0 locked (L=1), A=NAPOT, and no R/W/X permission.
LOCKED_NAPOT_CFG = 0x98


@dataclass(frozen=True)
class MemoryForm:
    """Which transfer shape one instruction uses."""

    #: Assembler-safe stem used in this form's labels.
    stem: str
    #: Whether the transfer takes a stride and moves one segment per row/column.
    strided: bool
    #: ``True`` for a load, which has a destination group but no memory write.
    is_load: bool


@dataclass(frozen=True)
class MemoryCase:
    """One case of the fault-atomicity recipe."""

    #: ``True`` for the later-wins overlap case, ``False`` for the fault case.
    overlap: bool


def transfer_bytes(machine: MachineConfig) -> int:
    """Bytes one whole-square transfer moves.

    At UDS 8 the raw, row/column-major, and strided forms all move exactly one
    square, so one length serves every form.
    """

    return machine.nelem * machine.uds // 8


def transfer_lines(
    mnemonic: str,
    form: MemoryForm,
    machine: MachineConfig,
    mreg: str,
    addr_reg: str,
    stride_reg: str,
) -> list[str]:
    """Emit one transfer of ``mreg`` and ``addr_reg``, with a stride if required."""

    if form.strided:
        return [
            f"    li      {stride_reg}, {machine.n}",
            f"    {mnemonic} {mreg}, {addr_reg}, {stride_reg}",
        ]
    return [f"    {mnemonic} {mreg}, {addr_reg}"]


def fill_region_lines(label: str, byte: int, byte_count: int) -> list[str]:
    """A labelled region pre-filled with one byte."""

    return [
        f".balign {byte_count}",
        f"{label}:",
        f"    .rept {byte_count}",
        f"    .byte {byte:#x}",
        "    .endr",
    ]


class MemoryFaultAtomicity(Template):
    """A transfer that raises an access fault commits nothing of the transfer."""

    name = "memory_fault_atomicity"
    dtypes = INTEGER

    def __init__(self, form: MemoryForm) -> None:
        """``form`` is the transfer shape the holding instruction uses."""

        self.form = form

    def fits(
        self,
        machine: MachineConfig,
        instruction: Instruction,
        dtype: DType | None = None,
    ) -> bool:
        if dtype is None or dtype.name != ELEMENT_DTYPE or machine.uds != TRANSFER_UDS:
            return False
        # A load case has no overlap body, so without a reachable fault it would
        # contribute nothing and the instruction would lose the template.
        return not self.form.is_load or self._fault_is_reachable(machine)

    def build(
        self, machine: MachineConfig, instruction: Instruction, dtype: DType | None
    ) -> Sequence[Case]:
        cases: list[Case] = []
        if not self.form.is_load:
            cases.append(Case(number=0, dtype=dtype, payload=MemoryCase(overlap=True)))
        if self._fault_is_reachable(machine):
            cases.append(
                Case(number=len(cases), dtype=dtype, payload=MemoryCase(overlap=False))
            )
        return cases

    def _fault_is_reachable(self, machine: MachineConfig) -> bool:
        """Whether the trigger lands inside this form's transfer extent.

        A strided transfer always reaches its second segment.  A contiguous
        transfer reaches the denied PMP region only when it is longer than that
        region.
        """

        if self.form.strided:
            return True
        return transfer_bytes(machine) > DENIED_REGION_OFFSET

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
        payload = case_payload(MemoryCase, case)
        prefix = f"case{case.number}_{self.form.stem}_"
        if payload.overlap:
            self._render_overlap(machine, instruction, prefix, out)
        elif self.form.is_load:
            self._render_load_fault(machine, instruction, prefix, out)
        else:
            self._render_store_fault(machine, instruction, prefix, out)

    def _render_overlap(
        self,
        machine: MachineConfig,
        instruction: Instruction,
        prefix: str,
        out: CaseOutput,
    ) -> None:
        size = transfer_bytes(machine)
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
            transfer_lines(instruction.name, self.form, machine, "m0", "t2", "t3")
        )
        out.text.extend(
            transfer_lines(instruction.name, self.form, machine, "m1", "t2", "t3")
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
        out.data.extend(fill_region_lines(window, UNTOUCHED_BYTE, size))
        out.data.append("")

    def _render_store_fault(
        self,
        machine: MachineConfig,
        instruction: Instruction,
        prefix: str,
        out: CaseOutput,
    ) -> None:
        size = transfer_bytes(machine)
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
        out.text.extend(self._fault_trigger_lines(instruction.name, window, "m0"))
        out.text.append(f"    EXPECT_TRAP_CAUSE 1, {STORE_ACCESS_FAULT_CAUSE}")
        out.text.extend(
            check_bytes_lines(
                window,
                [UNTOUCHED_BYTE] * size,
                tuple(range(self.checked_bytes(machine))),
            )
        )
        out.data.extend(
            repeated_square_lines(source, TRANSFER_BYTE, ELEMENT_BITS, machine)
        )
        out.data.extend(fill_region_lines(window, UNTOUCHED_BYTE, size))
        out.data.append("")

    def _render_load_fault(
        self,
        machine: MachineConfig,
        instruction: Instruction,
        prefix: str,
        out: CaseOutput,
    ) -> None:
        size = transfer_bytes(machine)
        prefill = f"{prefix}fault_prefill"
        source = f"{prefix}fault_src"
        window = f"{prefix}fault_dst"
        out.text.extend(
            [
                "    # a load that faults must leave its destination group alone",
                f"    li      t0, {ELEMENT_DTYPE}",
                "    msettyp m0, t0",
                f"    la      t1, {prefill}",
                f"    {RAW_LOAD_MNEMONIC:<8} m0, t1",
                "    TRAP_GUARD_ARM",
                f"    TRAP_GUARD_ACCEPT_CAUSE {LOAD_ACCESS_FAULT_CAUSE}",
            ]
        )
        out.text.extend(self._fault_trigger_lines(instruction.name, source, "m0"))
        out.text.append(f"    EXPECT_TRAP_CAUSE 1, {LOAD_ACCESS_FAULT_CAUSE}")
        # Copy the group out so a transfer that filled it before trapping shows up.
        out.text.extend(
            [
                f"    la      t2, {window}",
                f"    {RAW_STORE_MNEMONIC:<8} m0, t2",
            ]
        )
        out.text.extend(
            check_bytes_lines(
                window,
                [UNTOUCHED_BYTE] * size,
                tuple(range(self.checked_bytes(machine))),
            )
        )
        out.data.extend(fill_region_lines(prefill, UNTOUCHED_BYTE, size))
        out.data.extend(
            repeated_square_lines(source, TRANSFER_BYTE, ELEMENT_BITS, machine)
        )
        out.data.extend(fill_region_lines(window, UNTOUCHED_BYTE, size))
        out.data.append("")

    def _fault_trigger_lines(
        self, mnemonic: str, base: str, mreg: str
    ) -> list[str]:
        """Set up the fault, then issue the transfer that must not commit."""

        if self.form.strided:
            return [
                f"    la      t1, {base}",
                f"    li      t2, {NON_RAM_HOLE}",
                "    sub     t2, t2, t1",
                f"    {mnemonic} {mreg}, t1, t2",
            ]
        return [
            f"    la      t0, {base}",
            f"    addi    t0, t0, {DENIED_REGION_OFFSET}",
            "    srli    t0, t0, 2",
            "    ori     t0, t0, 1",
            "    csrw    pmpaddr0, t0",
            f"    li      t0, {LOCKED_NAPOT_CFG:#x}",
            "    csrw    pmpcfg0, t0",
            f"    la      t1, {base}",
            f"    {mnemonic} {mreg}, t1",
        ]


__all__ = [
    "DENIED_REGION_OFFSET",
    "ELEMENT_DTYPE",
    "LOAD_ACCESS_FAULT_CAUSE",
    "LOCKED_NAPOT_CFG",
    "MemoryCase",
    "MemoryFaultAtomicity",
    "MemoryForm",
    "NON_RAM_HOLE",
    "STORE_ACCESS_FAULT_CAUSE",
    "transfer_bytes",
    "transfer_lines",
]
