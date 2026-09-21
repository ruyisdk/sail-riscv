#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""The softfloat arithmetic special-value recipe: invalid operations.

These cases are the ones the IEEE rules make invalid or NaN-producing: a quiet
or signaling NaN operand, zero times infinity, and infinity minus infinity.
Every case clears amefflags, runs the instruction in its real operand order,
then requires both the NaN result and the exact flag set.  The operand that
carries the NaN differs per role -- the addend for the additive roles, the
destination for the fused-multiply roles -- so the role, not the mnemonic, drives
the case.
"""

from __future__ import annotations

DOC_ZH = """\
软浮点算术特殊值配方：无效运算。

这些用例是 IEEE 规则判为无效或产生 NaN 的用例：quiet 或 signaling NaN 操作数、零乘无穷、以及无穷减无穷。每个用例先清除 amefflags，按真实操作数顺序执行指令，然后同时要求 NaN 结果和精确的标志集合。携带 NaN 的操作数因角色而异——加法类角色是加数，融合乘类角色是目的方阵——因此驱动用例的是角色而不是助记符。
"""

from dataclasses import dataclass
from enum import Enum

from fp_semantics import FFLAGS_NV, FLOAT_BOUNDARIES

from mmul_gen.asm import check_dst_lines, repeated_square_lines
from mmul_gen.case_description import description_zh
from mmul_gen.machine import MachineConfig
from mmul_gen.templates.elementwise_forms import ElementwiseForm
from mmul_gen.templates.elementwise_float import case_registers
from mmul_gen.templates.elementwise_emit import (
    SCALAR,
    SCALAR_DEST,
    SOURCE,
    ZERO,
    CasePlan,
    Operand,
    plan_lines,
)

#: Formats without an infinity encoding.
NO_INFINITY_DTYPES = frozenset({"AME_OCP_E4M3_DTYPE"})


class FloatArithmeticRole(Enum):
    """Which invalid-operation vector one arithmetic instruction needs."""

    #: ``a + b``: infinity plus negative infinity is invalid.
    ADD = "add"
    #: ``a - b``: infinity minus infinity is invalid.
    SUB = "sub"
    #: ``|a - b|``: infinity minus infinity is invalid.
    ABSDIFF = "absdiff"
    #: ``a * b``: zero times infinity is invalid.
    MUL = "mul"
    #: ``-(a * b)``: zero times infinity is invalid.
    MULNEG = "mulneg"
    #: ``d + a * b``: the accumulator carries the NaN.
    MULACC = "mulacc"
    #: ``d - a * b``: additionally, infinity minus infinity is invalid.
    MULACCNEG = "mulaccneg"
    #: ``d + a * b`` with the addend as the destination.
    MULADD = "muladd"
    #: ``d - a * b`` with the addend as the destination.
    MULSUB = "mulsub"

    @property
    def negates_result(self) -> bool:
        """Whether the instruction negates its exact result."""

        return self in (
            FloatArithmeticRole.SUB,
            FloatArithmeticRole.MULNEG,
            FloatArithmeticRole.MULACCNEG,
            FloatArithmeticRole.MULSUB,
        )

    @property
    def always_positive_overflow(self) -> bool:
        """Whether the exact overflow result is positive whatever the input sign."""

        return self is FloatArithmeticRole.ABSDIFF

    @property
    def multiplies(self) -> bool:
        """Whether the operation forms a product that can underflow."""

        return self in (FloatArithmeticRole.MUL, FloatArithmeticRole.MULNEG) or self.fused

    @property
    def fused(self) -> bool:
        """Whether the operation multiplies and adds in one instruction."""

        return self in (
            FloatArithmeticRole.MULACC,
            FloatArithmeticRole.MULACCNEG,
            FloatArithmeticRole.MULADD,
            FloatArithmeticRole.MULSUB,
        )

    @property
    def addend_is_destination(self) -> bool:
        """Whether the fused operation adds its product into the destination."""

        return self in (FloatArithmeticRole.MULADD, FloatArithmeticRole.MULSUB)

    @property
    def has_halfway_case(self) -> bool:
        """Whether the role has a halfway case, which exists only in matrix forms."""

        return self in (FloatArithmeticRole.ADD, FloatArithmeticRole.MULACC)


@dataclass(frozen=True)
class FloatArithmeticCase:
    """One invalid-operation case: its operands, its answer, and its flags."""

    operands: dict[str, int]
    expected: int
    tag: str
    description: str
    squares: dict[str, str]

    def labelled(self, label_prefix: str) -> "FloatArithmeticCase":
        return FloatArithmeticCase(
            operands=self.operands,
            expected=self.expected,
            tag=self.tag,
            description=self.description,
            squares={
                "lhs": f"{label_prefix}lhs_square",
                "rhs": f"{label_prefix}rhs_square",
                "dest": f"{label_prefix}dest_square",
                "expected": f"{label_prefix}expected",
            },
        )


def input_operand_key(form: ElementwiseForm) -> str:
    """The operand the scalar form carries in a general-purpose register.

    The scalar and matrix forms name the same operand differently, so the cases
    below state their operands once and let this decide the key.
    """

    return "scalar" if form.takes_scalar else "lhs"


def nan_case_operands(
    role: FloatArithmeticRole,
    form: ElementwiseForm,
    nan: int,
    one: int,
) -> dict[str, int]:
    """The operands of one NaN case, with the NaN in the operand the role reads.

    The additive and multiplicative roles read the NaN as their second source,
    while a fused multiply reads it from the accumulator or from its product.
    """

    if role in (FloatArithmeticRole.ADD, FloatArithmeticRole.SUB,
                FloatArithmeticRole.ABSDIFF, FloatArithmeticRole.MUL,
                FloatArithmeticRole.MULNEG):
        return {input_operand_key(form): nan, "rhs": one, "dest": one}
    if role in (FloatArithmeticRole.MULACC, FloatArithmeticRole.MULACCNEG):
        return {"dest": nan, "lhs": one, "rhs": one, "scalar": one}
    if role in (FloatArithmeticRole.MULADD, FloatArithmeticRole.MULSUB):
        return {"dest": one, "lhs": nan, "rhs": one, "scalar": nan}
    raise ValueError(f"unsupported floating arithmetic role: {role}")


def float_arithmetic_cases(
    role: FloatArithmeticRole,
    form: ElementwiseForm,
    dtype_name: str,
    element_bits: int,
) -> tuple[FloatArithmeticCase, ...]:
    """Build the invalid-operation cases of one instruction and datatype."""

    values = FLOAT_BOUNDARIES[dtype_name]
    one = values["one"]
    nan = values["qnan"]
    snan = values["snan"]
    # The scalar form reads its second source from a general-purpose register.
    source = input_operand_key(form)
    inf = values["inf"]
    cases: list[FloatArithmeticCase] = []

    def add(
        name: str, operands: dict[str, int], expected: int, flags: int = 0
    ) -> None:
        cases.append(
            FloatArithmeticCase(
                operands={**operands, "flags": flags},
                expected=expected,
                tag=f"fp_{name}",
                description=f"浮点算术特殊值：{description_zh(name)}",
                squares={},
            )
        )

    add("quiet_nan", nan_case_operands(role, form, nan, one), nan)
    if snan is not None:
        add("signaling_nan", nan_case_operands(role, form, snan, one), nan, FFLAGS_NV)

    if dtype_name in NO_INFINITY_DTYPES:
        return tuple(cases)

    if role is FloatArithmeticRole.ADD:
        add("infinity_minus_infinity", {source: inf, "rhs": values["neg_inf"], "dest": one}, nan, FFLAGS_NV)
    elif role in (FloatArithmeticRole.SUB, FloatArithmeticRole.ABSDIFF):
        add("infinity_minus_infinity", {source: inf, "rhs": inf, "dest": one}, nan, FFLAGS_NV)
    elif role in (FloatArithmeticRole.MUL, FloatArithmeticRole.MULNEG):
        add("zero_times_infinity", {source: values["zero"], "rhs": inf, "dest": one}, nan, FFLAGS_NV)
    elif role in (FloatArithmeticRole.MULACC, FloatArithmeticRole.MULACCNEG):
        add(
            "zero_times_infinity",
            {"dest": one, "lhs": values["zero"], "rhs": inf, "scalar": values["zero"] if form.takes_scalar else one},
            nan,
            FFLAGS_NV,
        )
        if role is FloatArithmeticRole.MULACCNEG:
            add(
                "infinity_minus_infinity",
                {"dest": inf, "lhs": one, "rhs": inf, "scalar": one},
                nan,
                FFLAGS_NV,
            )
    elif role in (FloatArithmeticRole.MULADD, FloatArithmeticRole.MULSUB):
        add(
            "zero_times_infinity",
            {"dest": values["zero"], "lhs": one, "rhs": inf, "scalar": one},
            nan,
            FFLAGS_NV,
        )
        if role is FloatArithmeticRole.MULSUB:
            add(
                "infinity_minus_infinity",
                {"dest": inf, "lhs": inf, "rhs": one, "scalar": inf},
                nan,
                FFLAGS_NV,
            )
    return tuple(cases)


#: The destination, sources and operand order of each invalid-operation form.
ARITHMETIC_PLANS: dict[ElementwiseForm, CasePlan] = {
    ElementwiseForm.BINARY_M: CasePlan(
        (Operand("lhs", "t1", ZERO), Operand("rhs", "t2", SOURCE)), ZERO, (ZERO, SOURCE)
    ),
    ElementwiseForm.BINARY_X: CasePlan(
        (Operand("scalar", "t4"), Operand("rhs", "t2", ZERO)),
        SCALAR_DEST,
        (SCALAR, ZERO),
    ),
    ElementwiseForm.TERNARY_X: CasePlan(
        (
            Operand("dest", "t1", SCALAR_DEST),
            Operand("rhs", "t2", ZERO),
            Operand("scalar", "t4"),
        ),
        SCALAR_DEST,
        (SCALAR, ZERO),
    ),
}


@dataclass(frozen=True)
class ArithmeticShape:
    """One invalid-operation case's plan and the groups its header types."""

    plan: CasePlan
    typed_regs: tuple[int, ...]


def arithmetic_shape(
    form: ElementwiseForm,
    element_bits: int,
    machine: MachineConfig,
) -> ArithmeticShape:
    """The plan and the register set of one invalid-operation case.

    The ternary M form reads two register groups of its own, and which groups are
    free depends on the configured M-register file, so its plan is built here
    while the other forms take theirs from the table.
    """

    regs = case_registers(form, False, element_bits, machine)
    x_dest = regs.x_dest
    typed_regs = {0}
    if form is ElementwiseForm.TERNARY_M:
        assert regs.ternary_dest is not None
        dest_group, src1_group, src2_group = (
            regs.ternary_dest,
            regs.ternary_src1,
            regs.ternary_src2,
        )
        typed_regs.update({src1_group, src2_group})
        plan = CasePlan(
            operands=(
                Operand("dest", "t1", f"m{dest_group}"),
                Operand("lhs", "t1", f"m{src1_group}"),
                Operand("rhs", "t2", f"m{src2_group}"),
            ),
            dest=f"m{dest_group}",
            sources=(f"m{src1_group}", f"m{src2_group}"),
        )
    else:
        plan = ARITHMETIC_PLANS[form]
        if form is ElementwiseForm.BINARY_M:
            typed_regs.add(regs.source)
        else:
            typed_regs.add(x_dest)
    return ArithmeticShape(plan=plan, typed_regs=tuple(sorted(typed_regs)))


def float_arithmetic_case_lines(
    case: FloatArithmeticCase,
    form: ElementwiseForm,
    mnemonic: str,
    dtype_name: str,
    element_bits: int,
    case_number: int,
    machine: MachineConfig,
) -> list[str]:
    """The ``.text`` block of one invalid-operation case."""

    shape = arithmetic_shape(form, element_bits, machine)
    lines = [
        f"    # arithmetic special case {case_number}: {mnemonic} {dtype_name}",
        f"    li      t0, {dtype_name}",
        *[f"    msettyp m{reg}, t0" for reg in shape.typed_regs],
        "    csrw    amefflags, x0",
    ]
    if form in (ElementwiseForm.BINARY_X, ElementwiseForm.TERNARY_X):
        lines.append("    csrw    ame_scalar_dtype, t0")
    lines.extend(
        plan_lines(
            shape.plan,
            mnemonic,
            case.squares,
            lambda name: case.operands[name],
            element_bits,
            machine,
        )
    )
    lines.extend(
        [
            "    csrr    t4, amefflags",
            f"    EXPECT  t4, {case.operands['flags']}",
            *check_dst_lines(case.expected, element_bits, machine=machine),
        ]
    )
    return lines


def float_arithmetic_case_data(
    case: FloatArithmeticCase, element_bits: int, machine: MachineConfig
) -> list[str]:
    """The operand and destination squares of one invalid-operation case."""

    squares = case.squares
    values = case.operands
    lhs_value = values.get("lhs", values.get("scalar", values["dest"]))
    data = [
        *repeated_square_lines(squares["lhs"], lhs_value, element_bits, machine),
        *repeated_square_lines(squares["rhs"], values["rhs"], element_bits, machine),
        *repeated_square_lines(squares["dest"], values["dest"], element_bits, machine),
        "",
    ]
    return data


__all__ = [
    "NO_INFINITY_DTYPES",
    "FloatArithmeticCase",
    "FloatArithmeticRole",
    "float_arithmetic_case_data",
    "float_arithmetic_case_lines",
    "float_arithmetic_cases",
]
