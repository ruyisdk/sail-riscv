#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Broadcast one scalar into every storage slot of a narrower descriptor.

The descriptor is physically stored at half the active UDS, so a broadcast
still fills whole slots: the check reads the first and last byte of the square
and compares them with the repeated slot image, which catches both a short
write and a slot-alignment mistake.
"""

from __future__ import annotations

DOC_ZH = """\
将一个标量广播到较窄描述符的每个存储槽。

该描述符在物理上以有效 UDS 的一半存储，因此广播仍会填满整个槽：检查读取方阵的首字节与末字节并与重复的槽镜像比较，从而同时捕获写入过短和槽对齐错误。
"""

from collections.abc import Sequence
from typing import TYPE_CHECKING

from mmul_gen.asm import load_byte_lines
from mmul_gen.machine import PACKED_STORAGE, MachineConfig
from mmul_gen.templates.base import Case, CaseOutput, Template
from mmul_gen.templates.broadcast_common import (
    DESTINATION_LABEL,
    STORAGE_VALUE_BASE,
    ingress_case,
    label_index,
    packed_storage_bytes,
)

if TYPE_CHECKING:
    from mmul_gen.instruction import Instruction
    from mmul_gen.machine import DType


class PackedStorageBroadcast(Template):
    """Broadcast into the storage slots of a half-UDS descriptor."""

    summary_zh = "广播到半个 UDS 描述符的存储槽。"
    name = "packed_storage_ingress"
    dtypes = PACKED_STORAGE

    def build(
        self, machine: MachineConfig, instruction: Instruction, dtype: DType | None
    ) -> Sequence[Case]:
        return ingress_case(machine, dtype)

    def render(
        self,
        machine: MachineConfig,
        instruction: Instruction,
        case: Case,
        out: CaseOutput,
    ) -> None:
        if case.dtype is None:
            raise ValueError("a packed-storage broadcast case needs a datatype")
        element_bits = case.dtype.bits
        if not 0 < element_bits < machine.uds:
            raise ValueError(
                f"unsupported packed-storage broadcast: {case.dtype.name}/{element_bits}"
            )
        square_bytes = machine.nelem * machine.uds // 8
        index = label_index(machine, case.dtype, self.dtypes)
        value = (STORAGE_VALUE_BASE + index) & ((1 << element_bits) - 1)
        slot = packed_storage_bytes(value, element_bits, machine.uds)
        out.text.extend(
            [
                f"    # storage case {index}: {instruction.name} {case.dtype.name}",
                f"    li      t0, {case.dtype.name}",
                "    msettyp m0, t0",
                f"    li      t1, {value}",
                f"    {instruction.name} m0, t1, t0",
                f"    la      t2, {DESTINATION_LABEL}",
                "    mss.rm     m0, t2",
                f"    la      t3, {DESTINATION_LABEL}",
                "    lbu     t4, 0(t3)",
                f"    EXPECT  t4, {slot[0]}",
                *load_byte_lines("t4", "t3", square_bytes - 1),
                f"    EXPECT  t4, {slot[-1]}",
                "",
            ]
        )


__all__ = ["PackedStorageBroadcast"]


PACKED_STORAGE_INGRESS = PackedStorageBroadcast()
