#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Shared shape of the integer shift templates.

A shift forms one source operand, applies the shift, and stores the result.  The
two forms differ only in where the amount comes from: the register form reads a
second M operand holding one amount per element, the scalar form reuses a single
integer register for every element.  Both are driven by the same expected-value
function: the instruction's own ``evaluate``, handed over when the template is
constructed, so each direction states its formula in its own class.

The source pattern keeps the sign bit set in every element, and the amount sweep
walks ``0, 1, bits-1, bits, bits+1, 2*bits-1``: the amounts at and past the
element width pin down the hardware's modulo reduction of the amount, which is
the behaviour a plain shift-by-constant test would never reach.

Four-bit elements are packed two per ``.byte`` on one long line, so this shape
is emitted here rather than routed through the multi-per-line element emitter.
"""

from __future__ import annotations

DOC_ZH = """\
整数移位模板的共享形态。

移位形成一个源操作数，施加移位，再存储结果。两种形式只在位移量的来源上不同：寄存器形式读取第二个 M 操作数，其中每个元素一个位移量；标量形式对所有元素复用同一个整数寄存器。两者都由同一个期望值函数驱动：指令自己的 ``evaluate``，在构造模板时交入，因此每个方向都在自己的类里陈述算式。

源模式让每个元素的符号位保持置位，位移量扫描走过 ``0, 1, bits-1, bits, bits+1, 2*bits-1``：等于和超过元素宽度的位移量钉死硬件对位移量的取模归约，这是普通的按常量移位测试永远触及不到的行为。

4 位元素按两个一个 ``.byte`` 放在一个长行上，因此这里采用该形态，而不走多元素一行的发射器。
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar

from mmul_gen.asm import (
    check_dst_element_lines,
    data_element_lines,
    hex_value,
    pack_nibbles,
)
from mmul_gen.case_description import description_zh
from mmul_gen.machine import FORMED_INTEGER, MachineConfig, dtype_is_signed_int, dtype_stem
from mmul_gen.registers import choose_m_group_base
from mmul_gen.templates.base import Case, CaseOutput, Template, case_payload

if TYPE_CHECKING:
    from mmul_gen.instruction import Instruction
    from mmul_gen.machine import DType


#: The instruction's own formula: ``evaluate(instruction, value, amount, bits)``
#: as written on the instruction class.
IntegerShiftFormula = Callable[[Any, int, int, int], int]

#: The one input case every integer shift runs, in both forms.
INPUT_CASE = "sign and width edge values with modulo-reduced shift amounts"
#: Elements of the four-bit storage shape packed into one byte.
#: The preferred destination base, kept whenever the register file allows it.
PREFERRED_DESTINATION_BASE = 16
#: Positions sampled after a shift, capped by the square size on small machines.
CHECKED_POSITIONS = (0, 1, 2, 3, 4, 5)


@dataclass(frozen=True)
class ShiftPayload:
    """Source pattern, shift amounts, and expected results of one shift case."""

    source: tuple[int, ...]
    amounts: tuple[int, ...]
    expected: tuple[int, ...]
    #: The one amount every element uses, or ``None`` for the register form.
    scalar_amount: int | None


def shift_pattern_source_values(element_bits: int, element_count: int) -> list[int]:
    """Filler source whose every element carries the sign/MSB bit set."""

    mask = (1 << element_bits) - 1
    high_bit = 1 << (element_bits - 1)
    return [
        (high_bit | ((index * 13 + 5) & (high_bit - 1))) & mask
        for index in range(element_count)
    ]


def shift_edge_amount_values(element_bits: int, element_count: int) -> list[int]:
    """Shift-amount sweep over the interesting boundary amounts."""

    pattern = (0, 1, element_bits - 1, element_bits, element_bits + 1, 2 * element_bits - 1)
    return [pattern[index % len(pattern)] for index in range(element_count)]


def payload_data_lines(
    label: str, values: Sequence[int], element_bits: int, square_bytes: int
) -> list[str]:
    """One labelled input square, nibble-packed when the element is narrower."""

    lines = [f".balign {square_bytes}", f"{label}:"]
    if element_bits == 4:
        packed = pack_nibbles(list(values))
        return [*lines, "    .byte " + ", ".join(hex_value(v, 8) for v in packed)]
    return [*lines, *data_element_lines(values, element_bits)]


def destination_lines(label: str, square_bytes: int) -> list[str]:
    """The touched square, pre-filled so a partial write cannot pass."""

    return [
        f".balign {square_bytes}",
        f"{label}:",
        f"    .rept {square_bytes}",
        "    .byte 0xa5",
        "    .endr",
    ]


def shifted_check_lines(
    expected: Sequence[int], element_bits: int, label: str
) -> list[str]:
    """Sample the first positions and the last element of the shifted square."""

    lines: list[str] = []
    for index in sorted({*CHECKED_POSITIONS, len(expected) - 1}):
        lines.extend(check_dst_element_lines(expected[index], element_bits, index, label))
    return lines


class IntegerShiftTemplate(Template, family_base=True):
    """Shared plumbing of the register-form and scalar-form integer shifts."""

    dtypes = FORMED_INTEGER

    #: True when one scalar register supplies the amount for every element.
    scalar_amount: ClassVar[bool] = False

    def __init__(
        self, evaluate: IntegerShiftFormula, *, signed_only: bool = False
    ) -> None:
        """``evaluate`` is the instruction's formula; ``signed_only`` its support.

        An arithmetic right shift is defined on signed descriptors only, which
        the formula cannot state, so the instruction declares it alongside.
        """

        self.evaluate = evaluate
        self.signed_only = signed_only

    def fits(
        self,
        machine: MachineConfig,
        instruction: Instruction,
        dtype: DType | None = None,
    ) -> bool:
        if dtype is None:
            raise ValueError("an integer shift is always formed from a datatype")
        if self.signed_only and not dtype_is_signed_int(dtype.name):
            return False
        # The register form needs the source square and the amount square live
        # in the M file at the same time.
        if not self.scalar_amount and 2 * machine.nregs(dtype.bits) > machine.num_m_regs:
            return False
        return True

    def build(
        self,
        machine: MachineConfig,
        instruction: Instruction,
        dtype: DType | None,
    ) -> Sequence[Case]:
        if dtype is None:
            raise ValueError("an integer shift is always formed from a datatype")
        element_count = machine.storage_elements(dtype.bits)
        source = shift_pattern_source_values(dtype.bits, element_count)
        if self.scalar_amount:
            # One past the element width, so every element exercises the
            # hardware's modulo reduction of the amount.
            scalar = dtype.bits + 1
            amounts = [scalar] * element_count
        else:
            scalar = None
            amounts = shift_edge_amount_values(dtype.bits, element_count)
        expected = [
            self.evaluate(instruction, value, amount, dtype.bits)
            for value, amount in zip(source, amounts)
        ]
        payload = ShiftPayload(
            source=tuple(source),
            amounts=tuple(amounts),
            expected=tuple(expected),
            scalar_amount=scalar,
        )
        return [
            Case(
                number=0,
                dtype=dtype,
                payload=payload,
                description=description_zh(INPUT_CASE),
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
            raise ValueError("an integer shift is always formed from a datatype")
        payload = case_payload(ShiftPayload, case)
        element_bits = case.dtype.bits
        square_bytes = machine.square_bytes(element_bits)
        prefix = f"case{case.number}_{dtype_stem(case.dtype.name)}_"
        source_label = f"{prefix}source"
        shift_label = f"{prefix}shifts"
        destination_label = f"{prefix}destination"
        destination_reg = choose_m_group_base(
            machine.num_m_regs, element_bits, machine.uds, PREFERRED_DESTINATION_BASE
        )
        out.text.extend(
            [
                f"    # {instruction.name} {case.dtype.name}",
                f"    li      t0, {case.dtype.name}",
                "    msettyp m0, t0",
                f"    msettyp m{destination_reg}, t0",
                f"    la      t1, {source_label}",
                "    mls.rm     m0, t1",
            ]
        )
        out.data.extend(
            payload_data_lines(source_label, payload.source, element_bits, square_bytes)
        )
        if payload.scalar_amount is None:
            amount_reg = machine.nregs(element_bits)
            out.text.extend(
                [
                    f"    msettyp m{amount_reg}, t0",
                    f"    la      t1, {shift_label}",
                    f"    mls.rm     m{amount_reg}, t1",
                    f"    {instruction.name} m{destination_reg}, m0, m{amount_reg}",
                ]
            )
            out.data.extend(
                payload_data_lines(shift_label, payload.amounts, element_bits, square_bytes)
            )
        else:
            out.text.extend(
                [
                    f"    li      t4, {payload.scalar_amount}",
                    f"    {instruction.name} m{destination_reg}, t4, m0",
                ]
            )
        out.text.extend(
            [
                f"    la      t2, {destination_label}",
                f"    mss.rm     m{destination_reg}, t2",
                *shifted_check_lines(payload.expected, element_bits, destination_label),
            ]
        )
        out.data.extend(destination_lines(destination_label, square_bytes))
        out.data.append("")


__all__ = [
    "INPUT_CASE",
    "IntegerShiftFormula",
    "IntegerShiftTemplate",
    "ShiftPayload",
    "destination_lines",
    "payload_data_lines",
    "shift_edge_amount_values",
    "shift_pattern_source_values",
    "shifted_check_lines",
]
