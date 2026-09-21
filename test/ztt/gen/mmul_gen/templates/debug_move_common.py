#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Shared shape of the debug scalar/M-register move templates.

One width is one template: the case writes a scalar into an M register at an
element position with ``mmove<width>.m.x``, reads it back with
``mmove<width>.x.m``, and then checks the raw memory image with ``mss.rm``.  Both
directions are exercised inside the same case, so the ``.m.x`` and ``.x.m``
instructions share one template and differ only in their banner.

The debug position addresses the raw M-register bit view, which the manual
describes as N rows of ``(N * uds) / width`` elements.  A width wider than one
row cannot be placed at all -- the model raises an Illegal Instruction -- so such
a width has nothing to test here and the instruction produces no source in that
configuration.
"""

from __future__ import annotations

DOC_ZH = """\
调试标量/M 寄存器搬移模板的共享形态。

一种宽度一个模板：用例用 ``mmove<width>.m.x`` 把一个标量写入 M 寄存器的某个元素位置，用 ``mmove<width>.x.m`` 读回，再用 ``mss.rm`` 检查原始内存镜像。两个方向都在同一个用例内进行，因此 ``.m.x`` 与 ``.x.m`` 指令共用一个模板，只在横幅上不同。

调试位置寻址原始 M 寄存器位视图，手册将其描述为 N 行、每行 ``(N * uds) / width`` 个元素。宽于一行宽度的元素根本无法放置——模型会抛非法指令——因此这种宽度在这里没有可测内容，该指令在该配置下不产生源。
"""

from collections.abc import Sequence
from typing import TYPE_CHECKING, ClassVar

from mmul_gen.asm import hex_value
from mmul_gen.case_description import description_zh
from mmul_gen.machine import MachineConfig
from mmul_gen.templates.base import Case, CaseOutput, Template

if TYPE_CHECKING:
    from mmul_gen.instruction import Instruction
    from mmul_gen.machine import DType


#: The one input case every debug move runs, in both directions.
INPUT_CASE = "position_roundtrip_and_memory_image"
#: Label of the raw image the M register is stored into.
DESTINATION_LABEL = "debug_move_dst"


class DebugMoveTemplate(Template, family_base=True):
    """One debug move width, parameterised by the three constants below."""

    summary_zh = "一种调试搬移宽度，由下面三个常量参数化。"
    name = INPUT_CASE
    dtypes = None

    #: Width of the moved element, in bits.
    element_bits: ClassVar[int] = 0
    #: Element position inside the raw M-register bit view.
    position: ClassVar[int] = 0
    #: Pattern written into that element.
    value: ClassVar[int] = 0

    @property
    def write_mnemonic(self) -> str:
        return f"mmove{self.element_bits}.m.x"

    @property
    def read_mnemonic(self) -> str:
        return f"mmove{self.element_bits}.x.m"

    def fits(
        self, machine: MachineConfig, instruction: Instruction, dtype: DType | None = None
    ) -> bool:
        # A width wider than one row of the raw bit view has no legal position.
        return self.element_bits <= machine.n * machine.uds

    def build(
        self, machine: MachineConfig, instruction: Instruction, dtype: DType | None = None
    ) -> Sequence[Case]:
        return [Case(number=0, dtype=None, description=description_zh(self.name))]

    def render(
        self,
        machine: MachineConfig,
        instruction: Instruction,
        case: Case,
        out: CaseOutput,
    ) -> None:
        element_bytes = self.element_bits // 8
        expected = self.value & ((1 << self.element_bits) - 1)
        # The position wraps inside the raw bit view, whose width grows with
        # uds while N stays fixed for a generated suite.
        row_elements = max(1, machine.nelem * machine.uds // self.element_bits)
        byte_offset = (self.position % row_elements) * element_bytes
        destination_bytes = machine.nelem * machine.uds // 8

        out.text.extend(
            [
                "    li      t0, AME_UINT8_DTYPE",
                "    msettyp m0, t0",
                f"    li      t0, {self.position}",
                f"    li      t1, {hex_value(self.value, 64)}",
                f"    {self.write_mnemonic} m0, t1, t0",
                f"    {self.read_mnemonic} t3, m0, t0",
                f"    EXPECT  t3, {hex_value(expected, 64)}",
                f"    la      t5, {DESTINATION_LABEL}",
                "    mss.rm     m0, t5",
                f"    lbu     t4, {byte_offset}(t5)",
                f"    EXPECT  t4, {hex_value(expected & 0xFF, 8)}",
                f"    lbu     t4, {byte_offset + element_bytes - 1}(t5)",
                f"    EXPECT  t4, {hex_value(expected >> (8 * (element_bytes - 1)) & 0xFF, 8)}",
            ]
        )
        out.data.extend(
            [
                f".balign {destination_bytes}",
                f"{DESTINATION_LABEL}:",
                f"    .rept {destination_bytes}",
                "    .byte 0",
                "    .endr",
                "",
            ]
        )


__all__ = ["DESTINATION_LABEL", "INPUT_CASE", "DebugMoveTemplate"]
