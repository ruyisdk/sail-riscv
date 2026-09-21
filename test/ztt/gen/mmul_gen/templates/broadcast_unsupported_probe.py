#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""The unsupported-datatype ingress probe.

Ingress is descriptor-checked before it writes: broadcasting a UINT16 scalar
through a UINT8 descriptor must set the UN status bit and leave the
destination exactly as the seed left it.  The seeded square is compared byte
by byte at the boundaries, so a partial write is caught where a status-only
check would pass.
"""

from __future__ import annotations

DOC_ZH = """\
不支持 datatype 的入口探针。

入口在写入之前先做描述符检查：通过 UINT8 描述符广播一个 UINT16 标量必须置位 UN 状态位，并使目的方阵与播种时完全一致。被播种的方阵在边界处逐字节比较，因此仅检查状态的实现会漏掉的部分写入在这里会被捕获。
"""

from collections.abc import Sequence
from typing import TYPE_CHECKING

from mmul_gen.asm import check_dst_element_lines
from mmul_gen.machine import MachineConfig
from mmul_gen.templates.base import Case, CaseOutput, Template
from mmul_gen.templates.broadcast_common import (
    DESTINATION_LABEL,
    UNSUPPORTED_SOURCE_LABEL,
    unsupported_probe_data_lines,
    unsupported_probe_values,
)

if TYPE_CHECKING:
    from mmul_gen.instruction import Instruction
    from mmul_gen.machine import DType


#: Element positions sampled across the untouched destination square.
CHECKED_POSITIONS = (0, 1, 7)
#: The narrow descriptor the probe seeds the destination through.
SEED_DTYPE = "AME_UINT8_DTYPE"
#: The wide descriptor and scalar that must be rejected.
REJECTED_DTYPE = "AME_UINT16_DTYPE"
REJECTED_SCALAR = "0x1234"


class UnsupportedDtypeProbe(Template):
    """Prove an unsupported ingress is rejected without a partial write."""

    summary_zh = "证明不支持的入口被拒绝且没有部分写入。"
    name = "unsupported_dtype_probe"
    dtypes = None

    def build(
        self, machine: MachineConfig, instruction: Instruction, dtype: DType | None
    ) -> Sequence[Case]:
        return [Case(number=0, dtype=None)]

    def render(
        self,
        machine: MachineConfig,
        instruction: Instruction,
        case: Case,
        out: CaseOutput,
    ) -> None:
        values = unsupported_probe_values(machine.nelem)
        out.text.extend(
            [
                "    # Unsupported UINT16 -> UINT8 ingress sets UN and preserves md",
                f"    li      t0, {SEED_DTYPE}",
                "    msettyp m0, t0",
                f"    la      t2, {UNSUPPORTED_SOURCE_LABEL}",
                "    mls.rm     m0, t2",
                "    csrwi   amestatus, 0",
                f"    li      t0, {REJECTED_DTYPE}",
                f"    li      t4, {REJECTED_SCALAR}",
                f"    {instruction.name} m0, t4, t0",
                "    csrr    t1, amestatus",
                "    andi    t1, t1, 1",
                "    EXPECT  t1, 1",
                f"    la      t2, {DESTINATION_LABEL}",
                "    mss.rm     m0, t2",
            ]
        )
        for index in (*CHECKED_POSITIONS, machine.nelem - 1):
            out.text.extend(
                check_dst_element_lines(values[index], 8, index, DESTINATION_LABEL)
            )
        out.data.extend(unsupported_probe_data_lines(machine.nelem))


__all__ = ["UnsupportedDtypeProbe"]


UNSUPPORTED_DTYPE_PROBE = UnsupportedDtypeProbe()
