#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Strided transfer of a packed image whose squares are converted and widened.

The third strided-memory recipe: the storage descriptor is half the active UDS
and has a same-signedness twin at the full UDS, so the transfer is checked
through a real conversion -- widen on the way in, narrow on the way out -- rather
than through bit preservation alone.  Pair ``0`` is the unsigned pair and pair
``1`` the signed one, which is the numbering the labels print.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from mmul_gen.machine import (
    STRIDED_CONVERSION,
    MachineConfig,
    dtype_is_signed_int,
    dtype_stem,
)
from mmul_gen.templates.base import Case, CaseOutput, Template, domain_index
from mmul_gen.templates.strided_memory_common import (
    byte_fill_region_lines,
    byte_region_lines,
    linear_square_lines,
    packed_load_case_lines,
    packed_store_case_lines,
    segment_values,
    StridedTransfer,
)

if TYPE_CHECKING:  # pragma: no cover - typing only
    from mmul_gen.instruction import Instruction

#: Minimum distance between two segments of one packed pair image.
MIN_PAIR_SEGMENT_STRIDE = 8


class StridedConversionPairs(Template):
    """A half-UDS image widened to its full-UDS twin, one conversion pair at a time."""

    name = "strided_conversion_pairs"
    dtypes = STRIDED_CONVERSION

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
        storage_bits = machine.uds // 2
        is_signed = dtype_is_signed_int(dtype.name)
        compute_name = f"AME_{'INT' if is_signed else 'UINT'}{machine.uds}_DTYPE"
        index = domain_index(machine, dtype, STRIDED_CONVERSION)
        label_prefix = f"packed{index}_{dtype_stem(dtype.name)}_"
        source_label = f"{label_prefix}packed_src"
        square0_label = (
            f"{label_prefix}packed_square0_dst"
            if transfer.is_load
            else f"{label_prefix}packed_square0_src"
        )
        square1_label = (
            f"{label_prefix}packed_square1_dst"
            if transfer.is_load
            else f"{label_prefix}packed_square1_src"
        )
        destination_label = f"{label_prefix}packed_dst"
        segment_bytes = (
            machine.n * storage_bits // 8
            if transfer.transposed
            else 2 * machine.n * storage_bits // 8
        )
        stride = max(MIN_PAIR_SEGMENT_STRIDE, segment_bytes)
        segments = segment_values(
            transfer, storage_bits, machine.uds, machine.n, packed=True
        )
        if transfer.is_load:
            out.text.extend(
                packed_load_case_lines(
                    instruction.name,
                    dtype.name,
                    compute_name,
                    storage_bits,
                    machine.uds,
                    stride,
                    label_prefix,
                    is_signed,
                    machine.n,
                )
            )
            out.data.extend(
                byte_region_lines(source_label, segments, stride, storage_bits)
            )
            square_bytes = machine.square_bytes(machine.uds)
            out.data.extend(
                byte_fill_region_lines(square0_label, square_bytes, square_bytes)
            )
            out.data.extend(
                byte_fill_region_lines(square1_label, square_bytes, square_bytes)
            )
            return
        out.text.extend(
            packed_store_case_lines(
                instruction.name,
                transfer,
                dtype.name,
                compute_name,
                storage_bits,
                machine.uds,
                stride,
                label_prefix,
                machine.n,
            )
        )
        out.data.extend(linear_square_lines(square0_label, 0, machine.uds, machine))
        out.data.extend(linear_square_lines(square1_label, 1, machine.uds, machine))
        out.data.extend(
            byte_fill_region_lines(destination_label, stride * len(segments), stride)
        )
