#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""``mconv.ew`` storage/compute datatype conversion round trip.

The instruction converts a formed M square between a descriptor stored at half
the active UDS and its same-signedness twin at the full UDS.  One case exercises
both directions: a packed storage square is widened into a compute square and
stored back, then two compute squares are narrowed into one packed storage
square and stored back.  ``mconv.ew`` is ``md, ms1`` and addresses M registers
only, so no case declares a register layout.

The byte-image helpers (``data_lines``/``destination_lines``/``encoded_values``)
are the same generic M-square emitters the indexed packed-slot templates use:
``mconv.ew`` is the non-indexed counterpart of that conversion, so it reuses
them rather than restating the nibble-packing rule.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from mmul_gen.asm import (
    check_bytes_lines,
    check_dst_element_lines,
    data_element_lines,
    sign_extend,
)
from mmul_gen.case_description import description
from mmul_gen.machine import PACKED_CONVERSION, MachineConfig, dtype_is_signed_int
from mmul_gen.reference import packed_compute_dtype
from mmul_gen.templates.base import Case, CaseOutput, Template, case_payload
from mmul_gen.templates.pack_common import (
    data_lines,
    destination_lines,
    encoded_values,
)

if TYPE_CHECKING:
    from mmul_gen.instruction import Instruction
    from mmul_gen.machine import DType


#: The single input pattern this instruction runs, and the label printed ahead
#: of the whole case loop.
INPUT_CASE = "roundtrip_with_boundary_values"


@dataclass(frozen=True)
class StorageComputePair:
    """One packed-storage/widened-compute descriptor pair under test."""

    storage_dtype: str
    compute_dtype: str
    is_signed: bool


def _boundary_cycle(storage_bits: int) -> list[int]:
    """The seven boundary values the widened expectations rotate through."""

    storage_mask = (1 << storage_bits) - 1
    return [
        0,
        1,
        2,
        (1 << (storage_bits - 1)) - 1,
        1 << (storage_bits - 1),
        storage_mask - 1,
        storage_mask,
    ]


class MconvRoundtrip(Template):
    """Widen a packed storage square and narrow two compute squares back."""

    name = INPUT_CASE
    dtypes = PACKED_CONVERSION

    def build(
        self, machine: MachineConfig, instruction: Instruction, dtype: DType
    ) -> Sequence[Case]:
        # The whole conversion block carries one input label, ahead of the first
        # descriptor, so only the first case carries it.
        first = self.dtypes(machine)[0]
        return [
            Case(
                number=0,
                dtype=dtype,
                payload=StorageComputePair(
                    storage_dtype=dtype.name,
                    compute_dtype=packed_compute_dtype(dtype.name, machine.uds),
                    is_signed=dtype_is_signed_int(dtype.name),
                ),
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
        payload = case_payload(StorageComputePair, case)
        number = case.number
        storage_bits = case.dtype.bits
        compute_bits = machine.uds
        storage_mask = (1 << storage_bits) - 1
        storage_bytes = machine.square_bytes(storage_bits)
        compute_bytes = machine.square_bytes(compute_bits)

        pattern = _boundary_cycle(storage_bits)
        expand_values = [
            pattern[(index + number) % len(pattern)] & storage_mask
            for index in range(machine.storage_elements(storage_bits))
        ]
        if payload.is_signed:
            expand_compute = [
                sign_extend(value, storage_bits) & ((1 << compute_bits) - 1)
                for value in expand_values
            ]
        else:
            expand_compute = [
                value & ((1 << compute_bits) - 1) for value in expand_values
            ]

        compress_src0 = [
            ((index * 3) + 1 + number) & ((1 << compute_bits) - 1)
            for index in range(machine.nelem)
        ]
        compress_src1 = [
            ((index * 5) + 9 + number) & ((1 << compute_bits) - 1)
            for index in range(machine.nelem)
        ]
        compress_values = [
            value & storage_mask for value in compress_src0 + compress_src1
        ]

        stem = "signed" if payload.is_signed else "unsigned"
        prefix = f"case{number}_"
        expand_storage = f"{prefix}expand_storage"
        expand_compute0 = f"{prefix}expand_compute0"
        expand_compute1 = f"{prefix}expand_compute1"
        compress_compute0 = f"{prefix}compress_compute0"
        compress_compute1 = f"{prefix}compress_compute1"
        compress_storage = f"{prefix}compress_storage"

        out.text.extend(
            [
                f"    # case {number}: {instruction.name} {stem} storage/compute "
                "roundtrip",
                f"    li      t0, {payload.storage_dtype}",
                f"    li      t1, {payload.compute_dtype}",
                "    msettyp m0, t0",
                "    msettyp m2, t1",
                "    msettyp m3, t1",
                "",
                f"    la      t2, {expand_storage}",
                "    mls.rm     m0, t2",
                f"    {instruction.name} m2, m0",
                f"    la      t2, {expand_compute0}",
                "    mss.rm     m2, t2",
                f"    la      t2, {expand_compute1}",
                "    mss.rm     m3, t2",
            ]
        )

        check_indices = sorted({0, 1, machine.n - 1, machine.nelem - 1})
        for elem_index in check_indices:
            out.text.extend(
                check_dst_element_lines(
                    expand_compute[elem_index], compute_bits, elem_index, expand_compute0
                )
            )
        for elem_index in check_indices:
            source_index = machine.nelem + elem_index
            out.text.extend(
                check_dst_element_lines(
                    expand_compute[source_index], compute_bits, elem_index, expand_compute1
                )
            )

        out.text.extend(
            [
                # The runtime check loops reuse t0/t1, so reload the dtype
                # selectors before reconfiguring the compress phase.
                f"    li      t0, {payload.storage_dtype}",
                f"    li      t1, {payload.compute_dtype}",
                "    msettyp m0, t1",
                "    msettyp m1, t1",
                "    msettyp m4, t0",
                "",
                f"    la      t2, {compress_compute0}",
                "    mls.rm     m0, t2",
                f"    la      t2, {compress_compute1}",
                "    mls.rm     m1, t2",
                f"    {instruction.name} m4, m0",
                f"    la      t2, {compress_storage}",
                "    mss.rm     m4, t2",
            ]
        )
        out.text.extend(
            check_bytes_lines(
                compress_storage,
                encoded_values(compress_values, storage_bits),
                [0, 1, 2, storage_bytes - 2, storage_bytes - 1],
            )
        )
        out.text.append("")

        out.data.extend(
            data_lines(expand_storage, expand_values, storage_bits, machine)
        )
        out.data.extend(destination_lines(expand_compute0, compute_bits, machine))
        out.data.extend(destination_lines(expand_compute1, compute_bits, machine))
        out.data.extend([f".balign {compute_bytes}", f"{compress_compute0}:"])
        out.data.extend(data_element_lines(compress_src0, compute_bits))
        out.data.extend([f".balign {compute_bytes}", f"{compress_compute1}:"])
        out.data.extend(data_element_lines(compress_src1, compute_bits))
        out.data.extend(destination_lines(compress_storage, storage_bits, machine))
        out.data.append("")


__all__ = ["INPUT_CASE", "MconvRoundtrip", "StorageComputePair"]


MCONV_ROUNDTRIP = MconvRoundtrip()
