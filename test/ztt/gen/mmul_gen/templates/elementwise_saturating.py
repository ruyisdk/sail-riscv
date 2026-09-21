#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""The saturating elementwise recipe: edge operands that must set amexsat.

Only seven of the elementwise instructions saturate, and each one needs a
different operand pair to push its result out of range: adding one to the dtype
maximum, multiplying the maximum by two, subtracting from the floor, and so on.
Every case clears amexsat before the operation and requires it to be set after,
then compares the destination against the saturated value.

An instruction states the two halves itself, as two arguments of its saturating
template: ``expectation`` says which end of the range the result clamps to, and
``plan`` says which squares carry it there.
"""

from __future__ import annotations

DOC_ZH = """\
饱和 elementwise 配方：必须置位 amexsat 的边界操作数。

elementwise 指令中只有七条会饱和，每条都需要不同的操作数对把结果推出范围：给 datatype 最大值加一、最大值乘二、从下界做减法等。每个用例在运算前清除 amexsat，运算后要求它被置位，然后把目的方阵与饱和值比较。

指令自己陈述这两半，作为其饱和模板的两个参数：``expectation`` 指出结果钳到范围的哪一端，``plan`` 指出哪些方阵把它推过去。
"""

from dataclasses import dataclass
from enum import Enum

from mmul_gen.asm import check_dst_lines, repeated_square_lines
from mmul_gen.inputs import int_edge_value
from mmul_gen.machine import MachineConfig, dtype_is_signed_int
from mmul_gen.templates.elementwise_emit import CasePlan, plan_lines
from mmul_gen.templates.elementwise_forms import ElementwiseForm
from mmul_gen.templates.elementwise_integer import type_setup_lines

#: The seven operands a saturating case lays out, in emission order.
SATURATING_ROLES = (
    "max",
    "one",
    "two",
    "underflow_lhs",
    "underflow_rhs",
    "abs",
    "ternary_underflow_dest",
)


class SaturatingExpectation(Enum):
    """Which end of the representable range one saturating instruction hits."""

    #: The operation overflows and clamps to the dtype maximum.
    MAX = "max"
    #: The operation underflows and clamps to the dtype floor.
    MIN = "min"


@dataclass(frozen=True)
class SaturatingOperands:
    """The seven edge-value squares of one saturating case."""

    max: int
    one: int
    two: int
    underflow_lhs: int
    underflow_rhs: int
    abs: int
    ternary_underflow_dest: int

    def square_value(self, role: str) -> int:
        return getattr(self, role)


@dataclass(frozen=True)
class SaturatingCase:
    """One saturating case: its edge operands, its answer, and its labels."""

    operands: SaturatingOperands
    expected: int
    squares: dict[str, str]

    def labelled(self, label_prefix: str) -> "SaturatingCase":
        return SaturatingCase(
            operands=self.operands,
            expected=self.expected,
            squares={role: f"{label_prefix}{role}_square" for role in SATURATING_ROLES},
        )


def saturating_case(
    kind: SaturatingExpectation,
    mnemonic: str,
    form: ElementwiseForm,
    dtype_name: str,
    element_bits: int,
) -> SaturatingCase | None:
    """Build the one saturating case of this datatype, or ``None`` if none exists.

    The absolute value of an *unsigned* element is the identity, so its result
    can never leave the representable range and amexsat must stay clear; no
    saturating case exists for that combination, and expecting one would be
    architecturally wrong.
    """

    signed = dtype_is_signed_int(dtype_name)
    if form is ElementwiseForm.UNARY_ABS and not signed:
        return None
    min_value = int_edge_value(dtype_name, element_bits, "lower_bound")
    max_value = int_edge_value(dtype_name, element_bits, "upper_bound")
    floor_value = min_value if signed else 0
    operands = SaturatingOperands(
        max=max_value,
        one=1,
        two=2,
        underflow_lhs=1,
        underflow_rhs=floor_value,
        abs=int_edge_value(dtype_name, element_bits, "abs_boundary"),
        ternary_underflow_dest=floor_value,
    )
    expected = max_value if kind is SaturatingExpectation.MAX else floor_value
    return SaturatingCase(operands=operands, expected=expected, squares={})


def saturating_case_lines(
    case: SaturatingCase,
    plan: CasePlan,
    form: ElementwiseForm,
    mnemonic: str,
    dtype_name: str,
    element_bits: int,
    case_number: int,
    machine: MachineConfig,
) -> list[str]:
    """The ``.text`` block of one saturating case."""

    lines = [
        f"    # saturating case {case_number}: {mnemonic} {dtype_name}",
        *type_setup_lines(
            dtype_name,
            element_bits,
            machine,
            include_x_dest=form
            in (ElementwiseForm.BINARY_X, ElementwiseForm.TERNARY_X),
            include_source=form is not ElementwiseForm.UNARY_ABS,
        ),
        "    li      t6, 0",
        "    csrw    amexsat, t6",
    ]
    if form in (ElementwiseForm.BINARY_X, ElementwiseForm.TERNARY_X):
        lines.insert(-1, "    csrw    ame_scalar_dtype, t0")
    lines.extend(
        plan_lines(
            plan,
            mnemonic,
            case.squares,
            case.operands.square_value,
            element_bits,
            machine,
        )
    )
    lines.extend(
        [
            "    csrr    t5, amexsat",
            "    EXPECT  t5, 1",
            *check_dst_lines(case.expected, element_bits, machine=machine),
        ]
    )
    return lines


def saturating_case_data(
    case: SaturatingCase, element_bits: int, machine: MachineConfig
) -> list[str]:
    """The seven edge-value squares of one saturating case."""

    data: list[str] = []
    for role in SATURATING_ROLES:
        data.extend(
            repeated_square_lines(
                case.squares[role],
                case.operands.square_value(role),
                element_bits,
                machine,
            )
        )
    return data


__all__ = [
    "SATURATING_ROLES",
    "SaturatingCase",
    "SaturatingExpectation",
    "SaturatingOperands",
    "saturating_case",
    "saturating_case_data",
    "saturating_case_lines",
]
