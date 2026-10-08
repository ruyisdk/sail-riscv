#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""The indexed pack template: a compute square narrowed into a storage slot.

Each case converts one compute square into the selected slot of a packed
storage square while the other slot keeps the value it was loaded with, and
verifies both the converted slot and the preserved one.
"""

from __future__ import annotations

from mmul_gen.templates.base import case_payload
from mmul_gen.templates.pack_common import (
    SLOT,
    PackedSlotConversion,
    PackedSlotPayload,
    boundary_values,
    byte_check_lines,
    case_source_values,
    data_lines,
    destination_lines,
    encoded_values,
    preserved_slot,
)


class PackSlots(PackedSlotConversion):
    """Narrow a whole-register compute square into one packed storage slot."""

    name = "packed_slot_write"

    def render(self, machine, instruction, case, out):
        payload = case_payload(PackedSlotPayload, case)
        number = case.number
        nelem = machine.nelem
        storage_bits = machine.uds // 2
        compute_bits = machine.uds
        prefix = f"pack{number}_"
        packed_input = f"{prefix}packed_input"
        source_label = f"{prefix}source"
        result_label = f"{prefix}result"

        source = case_source_values(number, compute_bits, nelem, payload.input_case)
        preserved = preserved_slot(number, storage_bits, nelem)
        initial_slot = boundary_values(number + 3, storage_bits, nelem)
        expected_values = preserved + [
            value & ((1 << storage_bits) - 1) for value in source
        ]
        expected = encoded_values(expected_values, storage_bits)
        input_values = preserved + initial_slot

        out.text.extend(
            [
                f"    # {instruction.name} {payload.storage_dtype} <- "
                f"{payload.compute_dtype}, slot {SLOT} selects slot 1",
                f"    li      t0, {payload.storage_dtype}",
                f"    li      t1, {payload.compute_dtype}",
                "    msettyp m0, t0",
                "    msettyp m2, t1",
                f"    la      t2, {packed_input}",
                "    mls.rm     m0, t2",
                f"    la      t2, {source_label}",
                "    mls.rm     m2, t2",
                f"    li      t4, {SLOT}",
                f"    {instruction.name} m0, t4, m2",
                f"    la      t2, {result_label}",
                "    mss.rm     m0, t2",
            ]
        )
        out.text.extend(byte_check_lines(result_label, expected))

        out.data.extend(data_lines(packed_input, input_values, storage_bits, machine))
        out.data.extend(data_lines(source_label, source, compute_bits, machine))
        out.data.extend(destination_lines(result_label, storage_bits, machine))
        out.data.append("")


__all__ = ["PackSlots"]


PACK_SLOTS = PackSlots()
