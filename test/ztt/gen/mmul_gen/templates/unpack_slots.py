#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""The indexed unpack template: a packed storage slot widened into a square.

Each case reads the selected slot of a packed storage square, widens it into
the compute descriptor, and verifies the converted elements; a signed storage
descriptor is sign-extended before it is masked into the wider element.
"""

from __future__ import annotations

DOC_ZH = """\
索引解包模板：将打包存储槽扩展为方阵。

每个用例读取打包存储方阵的选定槽，把它扩展为计算描述符，并验证转换后的元素；有符号存储描述符在掩码进更宽元素之前先做符号扩展。
"""

from mmul_gen.asm import sign_extend
from mmul_gen.templates.base import case_payload
from mmul_gen.templates.pack_common import (
    SLOT,
    PackedSlotConversion,
    PackedSlotPayload,
    case_source_values,
    data_lines,
    destination_lines,
    element_check_lines,
    preserved_slot,
)


class UnpackSlots(PackedSlotConversion):
    """Widen one packed storage slot into a whole-register compute square."""

    summary_zh = "将一个打包存储槽扩展为整寄存器的计算方阵。"
    name = "packed_slot_read"

    def render(self, machine, instruction, case, out):
        payload = case_payload(PackedSlotPayload, case)
        number = case.number
        nelem = machine.nelem
        storage_bits = machine.uds // 2
        compute_bits = machine.uds
        prefix = f"unpack{number}_"
        packed_input = f"{prefix}packed_input"
        result_label = f"{prefix}result"

        preserved = preserved_slot(number, storage_bits, nelem)
        selected_slot = case_source_values(
            number + 1, storage_bits, nelem, payload.input_case
        )
        packed_values = preserved + selected_slot
        expected = [
            sign_extend(value, storage_bits) & ((1 << compute_bits) - 1)
            if payload.is_signed
            else value
            for value in selected_slot
        ]

        out.text.extend(
            [
                f"    # {instruction.name} {payload.compute_dtype} <- "
                f"{payload.storage_dtype}, slot {SLOT} selects slot 1",
                f"    li      t0, {payload.storage_dtype}",
                f"    li      t1, {payload.compute_dtype}",
                "    msettyp m0, t0",
                "    msettyp m2, t1",
                f"    la      t2, {packed_input}",
                "    mls.rm     m0, t2",
                f"    li      t4, {SLOT}",
                f"    {instruction.name} m2, t4, m0",
                f"    la      t2, {result_label}",
                "    mss.rm     m2, t2",
            ]
        )
        out.text.extend(element_check_lines(result_label, expected, compute_bits, nelem))

        out.data.extend(data_lines(packed_input, packed_values, storage_bits, machine))
        out.data.extend(destination_lines(result_label, compute_bits, machine))
        out.data.append("")


__all__ = ["UnpackSlots"]


UNPACK_SLOTS = UnpackSlots()
