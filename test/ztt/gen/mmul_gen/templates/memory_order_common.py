#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Shared shape of the row/column-major memory-order templates.

The case loads the table in one addressing mode (``mls.rm`` or ``mls.cm``) and
stores the same M register back in the other (``mss.cm`` or ``mss.rm``).  The
stored square therefore re-encodes the linear element index through the
(row, column) of the active square size: an ``rm`` -> ``cm`` trip puts element
``(r, c)`` at column-major offset ``c * N + r``, and a ``cm`` -> ``rm`` trip
restores the linear order.

Both mnemonics of one trip run inside the same case, so the load and the store
instruction share one template and differ only in their banner and in the
``# case`` label.  The three edge checks pin down the two elements that tell the
two orders apart -- the second element and the first element of the next storage
row -- so the expectations are a generation-time function of N.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, ClassVar

from mmul_gen.asm import data_element_lines, row_col_values
from mmul_gen.case_description import description
from mmul_gen.machine import (
    INTEGER,
    MachineConfig,
    dtype_stem,
)
from mmul_gen.templates.base import Case, CaseOutput, Template

if TYPE_CHECKING:
    from mmul_gen.instruction import Instruction
    from mmul_gen.machine import DType


#: The one input case every memory-order instruction runs.
INPUT_CASE = "row_column_roundtrip_with_edge_checks"
#: Fill byte of the destination square no store wrote.
UNTOUCHED_BYTE = 0xA5


class MemoryOrderTemplate(Template, family_base=True):
    """One direction of the row/column-major round trip."""

    name = INPUT_CASE
    dtypes = INTEGER

    #: Addressing mode the load instruction uses (``"rm"`` or ``"cm"``).
    source_order: ClassVar[str] = "rm"
    #: Addressing mode the store instruction uses.
    destination_order: ClassVar[str] = "cm"

    @property
    def load_mnemonic(self) -> str:
        return f"mls.{self.source_order}"

    @property
    def store_mnemonic(self) -> str:
        return f"mss.{self.destination_order}"

    def build(
        self, machine: MachineConfig, instruction: Instruction, dtype: DType
    ) -> Sequence[Case]:
        # The whole round trip carries one label, ahead of the first descriptor,
        # so only the first case carries it.
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
        if case.dtype is None:
            raise ValueError("a memory-order case needs a datatype")
        element_bits = case.dtype.bits
        if element_bits not in {8, 16, 32, 64}:
            raise ValueError(f"unsupported memory-order element width: {element_bits}")

        element_bytes = element_bits // 8
        square_bytes = machine.nelem * element_bytes
        prefix = f"case{case.number}_{dtype_stem(case.dtype.name)}_"
        source_label = f"{prefix}src_{self.source_order}"
        destination_label = f"{prefix}dst_{self.destination_order}"
        # After the round trip the destination's second element holds
        # M[1][0] = N+1 and the first element of the next storage row holds
        # M[0][1] = 2, in one order or the other.
        if self.destination_order == "cm":
            expected_second, expected_next_row = machine.n + 1, 2
        else:
            expected_second, expected_next_row = 2, machine.n + 1

        out.text.extend(
            [
                f"    # case {case.number}: {instruction.name} {case.dtype.name}",
                f"    li      t0, {case.dtype.name}",
                "    msettyp m0, t0",
                "",
                f"    la      t1, {source_label}",
                f"    {self.load_mnemonic}  m0, t1",
                f"    la      t2, {destination_label}",
                f"    {self.store_mnemonic}  m0, t2",
                f"    la      t3, {destination_label}",
                "    lbu     t4, 0(t3)",
                "    EXPECT  t4, 1",
                f"    lbu     t4, {element_bytes}(t3)",
                f"    EXPECT  t4, {expected_second}",
                f"    lbu     t4, {machine.n * element_bytes}(t3)",
                f"    EXPECT  t4, {expected_next_row}",
                "",
            ]
        )
        out.data.extend(
            [
                f".balign {square_bytes}",
                f"{source_label}:",
                *data_element_lines(
                    row_col_values(self.source_order, machine.n, machine.nelem),
                    element_bits,
                ),
                f".balign {square_bytes}",
                f"{destination_label}:",
                f"    .rept {square_bytes}",
                f"    .byte 0x{UNTOUCHED_BYTE:02x}",
                "    .endr",
                "",
            ]
        )


__all__ = ["INPUT_CASE", "UNTOUCHED_BYTE", "MemoryOrderTemplate"]
