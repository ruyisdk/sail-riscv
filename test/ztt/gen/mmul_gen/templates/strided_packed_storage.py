#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Bit-preserving strided transfer of a sub-UDS packed image.

The second strided-memory recipe: every descriptor stored narrower than the UDS
forms ``UDS / element_bits`` logical squares in one physical M register, and the
transfer moves the packed slots without converting anything.  It runs on the
storage descriptors directly rather than through an integer-only conversion, so
saturating and floating descriptors are covered too.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from mmul_gen.machine import STRIDED_STORAGE, MachineConfig, dtype_stem
from mmul_gen.templates.base import Case, CaseOutput, Template, domain_index
from mmul_gen.templates.strided_memory_common import (
    byte_fill_region_lines,
    byte_region_lines,
    packed_linear_region_lines,
    packed_storage_load_case_lines,
    packed_storage_store_case_lines,
    segment_values,
    StridedTransfer,
)

if TYPE_CHECKING:  # pragma: no cover - typing only
    from mmul_gen.instruction import Instruction

#: Minimum distance between two segments of one packed source image.
MIN_PACKED_SEGMENT_STRIDE = 8


class StridedPackedStorage(Template):
    """A sub-UDS image moved slot by slot, for every packed storage descriptor."""

    name = "strided_packed_storage"
    dtypes = STRIDED_STORAGE

    def __init__(self, transfer: StridedTransfer) -> None:
        """``transfer`` is the direction and order this instruction moves data in."""

        self.transfer = transfer

    def build(
        self, machine: MachineConfig, instruction: "Instruction", dtype: object
    ) -> tuple[Case, ...]:
        return (Case(number=0, dtype=cast(object, dtype)),)

    def render(
        self,
        machine: MachineConfig,
        instruction: "Instruction",
        case: Case,
        out: CaseOutput,
    ) -> None:
        transfer = self.transfer
        dtype = case.dtype
        assert dtype is not None
        storage_bits = dtype.bits
        index = domain_index(machine, dtype, STRIDED_STORAGE)
        label_prefix = f"storage{index}_{dtype_stem(dtype.name)}_"
        source_label = f"{label_prefix}storage_src"
        destination_label = f"{label_prefix}storage_dst"
        pack_factor = machine.uds // storage_bits
        segment_bytes = (
            machine.n * storage_bits // 8
            if transfer.transposed
            else pack_factor * machine.n * storage_bits // 8
        )
        stride = max(MIN_PACKED_SEGMENT_STRIDE, segment_bytes)
        segments = segment_values(
            transfer, storage_bits, machine.uds, machine.n, packed=True
        )
        if transfer.is_load:
            out.text.extend(
                packed_storage_load_case_lines(
                    instruction.name,
                    dtype.name,
                    storage_bits,
                    machine.uds,
                    stride,
                    label_prefix,
                    machine.n,
                )
            )
            square_bytes = machine.square_bytes(storage_bits)
            out.data.extend(
                byte_region_lines(source_label, segments, stride, storage_bits)
            )
            out.data.extend(
                byte_fill_region_lines(destination_label, square_bytes, square_bytes)
            )
            return
        out.text.extend(
            packed_storage_store_case_lines(
                instruction.name,
                transfer,
                dtype.name,
                storage_bits,
                machine.uds,
                stride,
                label_prefix,
                machine.n,
            )
        )
        out.data.extend(
            packed_linear_region_lines(
                source_label, storage_bits, machine.uds, machine.n
            )
        )
        out.data.extend(
            byte_fill_region_lines(destination_label, stride * len(segments), stride)
        )
