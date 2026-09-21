#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Whole-square strided transfer, one element per segment.

The first of the three strided-memory recipes, and the one every descriptor at
or above the UDS takes: a strided load reads one element per segment, a strided
store writes one element per segment, and a stride of zero overlaps every
segment onto the same address.  Each datatype gets private labels because one
generated source carries the whole datatype matrix.
"""

from __future__ import annotations

DOC_ZH = """\
整方阵步长搬运，每段一个元素。

三种步长内存配方的第一种，也是所有大于等于 UDS 的描述符采用的那种：步长加载每段读一个元素，步长存储每段写一个元素，步长为零时所有段重叠到同一地址。每个 datatype 都有私有标签，因为一个生成源承载整个 datatype 矩阵。
"""

from typing import TYPE_CHECKING, cast

from mmul_gen.machine import SEMANTIC, MachineConfig, dtype_stem
from mmul_gen.templates.base import Case, CaseOutput, Template, domain_index
from mmul_gen.templates.strided_memory_common import (
    StridedTransfer,
    byte_fill_region_lines,
    byte_region_lines,
    normal_linear_square_lines,
    normal_load_case_lines,
    normal_store_case_lines,
    segment_values,
)

if TYPE_CHECKING:  # pragma: no cover - typing only
    from mmul_gen.instruction import Instruction

#: Minimum distance between two segments of one strided source image.
MIN_SEGMENT_STRIDE = 16


class StridedNormalSquare(Template):
    """A whole square moved one element per segment, for every semantic datatype."""

    summary_zh = "每个语义 datatype 都按每段一个元素搬移整个方阵。"
    name = "strided_normal_square"
    dtypes = SEMANTIC

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
        element_bits = dtype.bits
        index = domain_index(machine, dtype, SEMANTIC)
        label_prefix = f"case{index}_{dtype_stem(dtype.name)}_"
        source_label = f"{label_prefix}normal_src"
        destination_label = f"{label_prefix}normal_dst"
        overlap_label = f"{label_prefix}normal_overlap"
        stride = max(MIN_SEGMENT_STRIDE, machine.n * element_bits // 8)
        if transfer.is_load:
            out.text.extend(
                normal_load_case_lines(
                    instruction.name,
                    transfer,
                    dtype.name,
                    element_bits,
                    stride,
                    label_prefix,
                    machine.n,
                )
            )
            square_bytes = machine.square_bytes(element_bits)
            out.data.extend(
                byte_region_lines(
                    source_label,
                    segment_values(transfer, element_bits, element_bits, machine.n),
                    stride,
                    element_bits,
                )
            )
            out.data.extend(
                byte_fill_region_lines(destination_label, square_bytes, square_bytes)
            )
            return
        out.text.extend(
            normal_store_case_lines(
                instruction.name,
                transfer,
                dtype.name,
                element_bits,
                stride,
                label_prefix,
                machine.n,
            )
        )
        out.data.extend(
            normal_linear_square_lines(source_label, element_bits, machine)
        )
        out.data.extend(
            byte_fill_region_lines(destination_label, stride * machine.n, stride)
        )
        out.data.extend(byte_fill_region_lines(overlap_label, stride, stride))
