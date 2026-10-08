#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""The special-value softfloat recipe: NaN, infinity, and signed zero.

These nine instructions do not compute a nominal value; they pin down what the
format's special encodings do.  An instruction states which behaviour it has as
the single ``FloatSpecialRole`` it hands its template -- for a comparison, that role
also names which way it comes out on the special operands.  Each case clears amefflags, runs one operation,
then requires both the destination value and the exact flag set.  E4M3 has no
infinity or signaling-NaN encoding, so those cases are not produced for it.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from fp_semantics import FFLAGS_NV, FLOAT_BOUNDARIES

from mmul_gen.asm import check_dst_lines, repeated_square_lines
from mmul_gen.case_description import description
from mmul_gen.machine import MachineConfig
from mmul_gen.templates.elementwise_forms import ElementwiseForm
from mmul_gen.templates.elementwise_float import (
    case_registers,
    float_comparison_result_dtype,
)
from mmul_gen.templates.elementwise_emit import (
    SCALAR,
    SCALAR_DEST,
    SOURCE,
    ZERO,
    CasePlan,
    Operand,
    plan_lines,
)

#: Formats without an infinity or signaling-NaN encoding.
NO_INFINITY_DTYPES = frozenset({"AME_OCP_E4M3_DTYPE"})


class FloatSpecialRole(Enum):
    """How one instruction participates in the special-value template."""

    #: Absolute value: sign handling only.
    ABS = "abs"
    #: A comparison whose result on the special operands is a full mask.
    COMPARE_TRUE = "compare_true"
    #: A comparison whose result on the special operands is all zeros.
    COMPARE_FALSE = "compare_false"
    #: Maximum: a NaN operand is not selected, and signed zero prefers +0.
    MAX = "max"
    #: Minimum: the mirror image of maximum.
    MIN = "min"

    @property
    def holds(self) -> bool | None:
        """The special-operand outcome of a comparison role, else ``None``.

        Which way a comparison comes out on the special operands is a fact about
        the predicate, not about the nominal pair: a signed-zero pair satisfies
        ``>=`` but not ``<``, so the two comparisons disagree here even when
        their nominal answers agree.
        """

        if self is FloatSpecialRole.COMPARE_TRUE:
            return True
        if self is FloatSpecialRole.COMPARE_FALSE:
            return False
        return None

    @property
    def is_comparison(self) -> bool:
        """Whether this role is a comparison."""

        return self.holds is not None


@dataclass(frozen=True)
class FloatSpecialCase:
    """One special-value case: its two operands, its answer, and its flags."""

    operands: dict[str, int]
    expected: int
    tag: str
    description: str
    squares: dict[str, str]

    def labelled(self, label_prefix: str) -> "FloatSpecialCase":
        return FloatSpecialCase(
            operands=self.operands,
            expected=self.expected,
            tag=self.tag,
            description=self.description,
            squares={
                "lhs": f"{label_prefix}lhs_square",
                "rhs": f"{label_prefix}rhs_square",
                "value": f"{label_prefix}value_square",
                "expected": f"{label_prefix}expected",
            },
        )


def float_special_cases(
    role: FloatSpecialRole,
    dtype_name: str,
    element_bits: int,
) -> tuple[FloatSpecialCase, ...]:
    """Build the special-value cases of one instruction and datatype.

    Whether a comparison holds on the special operands is part of ``role``, and
    it is *not* the nominal template's outcome: ``mcmpge`` is false for the nominal
    pair (its first operand is the smaller one) yet true for signed zeros and
    infinities.  The nominal outcome belongs to the nominal template.
    """

    values = FLOAT_BOUNDARIES[dtype_name]
    has_infinity = dtype_name not in NO_INFINITY_DTYPES
    sign_bit = 1 << (element_bits - 1)
    cases: list[FloatSpecialCase] = []

    def add(name: str, lhs: int, rhs: int, expected: int, flags: int = 0) -> None:
        cases.append(
            FloatSpecialCase(
                operands={"lhs": lhs, "rhs": rhs, "value": lhs, "flags": flags},
                expected=expected,
                tag=f"fp_{name}",
                description=f"float special value: {description(name)}",
                squares={},
            )
        )

    if role is FloatSpecialRole.ABS:
        add("signed_zero", values["neg_zero"], 0, values["zero"])
        if has_infinity:
            add("negative_infinity", values["neg_inf"], 0, values["inf"])
        add("negative_qnan", values["qnan"] | sign_bit, 0, values["qnan"])
        return tuple(cases)

    if role.is_comparison:
        comparison_is_true = role.holds
        true_value = (1 << element_bits) - 1
        ordered = true_value if comparison_is_true else 0
        add("signed_zero", values["neg_zero"], values["zero"], ordered)
        add("quiet_nan", values["qnan"], values["one"], 0, FFLAGS_NV)
        if values["snan"] is not None:
            add("signaling_nan", values["snan"], values["one"], 0, FFLAGS_NV)
        if has_infinity:
            add("positive_infinity", values["inf"], values["one"], ordered)
            add(
                "negative_infinity",
                values["neg_inf"],
                values["one"],
                true_value if not comparison_is_true else 0,
            )
        return tuple(cases)

    if role not in (FloatSpecialRole.MAX, FloatSpecialRole.MIN):
        raise ValueError(f"unsupported float special-value role: {role}")
    prefer_max = role is FloatSpecialRole.MAX
    add(
        "signed_zero",
        values["neg_zero"],
        values["zero"],
        values["zero"] if prefer_max else values["neg_zero"],
    )
    add("quiet_nan", values["qnan"], values["one"], values["qnan"])
    if values["snan"] is not None:
        add("signaling_nan", values["snan"], values["one"], values["qnan"], FFLAGS_NV)
    if has_infinity:
        add(
            "positive_infinity",
            values["inf"],
            values["one"],
            values["inf"] if prefer_max else values["one"],
        )
        add(
            "negative_infinity",
            values["neg_inf"],
            values["one"],
            values["one"] if prefer_max else values["neg_inf"],
        )
    return tuple(cases)


#: The destination, sources and operand order of each special-value form.
SPECIAL_PLANS: dict[ElementwiseForm, CasePlan] = {
    ElementwiseForm.BINARY_M: CasePlan(
        (Operand("lhs", "t1", ZERO), Operand("rhs", "t2", SOURCE)), ZERO, (ZERO, SOURCE)
    ),
    ElementwiseForm.BINARY_X: CasePlan(
        (Operand("lhs", "t4"), Operand("rhs", "t2", ZERO)),
        SCALAR_DEST,
        (SCALAR, ZERO),
    ),
    ElementwiseForm.UNARY_ABS: CasePlan((Operand("value", "t1", ZERO),), ZERO, (ZERO,)),
}


@dataclass(frozen=True)
class SpecialShape:
    """One special-value case's plan and the groups its header types."""

    plan: CasePlan
    typed_regs: tuple[int, ...]
    result_reg: int | None


def special_shape(
    form: ElementwiseForm,
    is_comparison: bool,
    element_bits: int,
    machine: MachineConfig,
) -> SpecialShape:
    """The plan and the register set of one special-value case.

    A comparison writes a group of its own and reads its second operand from a
    group disjoint from m0.  Which groups are free depends on the configured
    M-register file, so the plan is built here instead of being fixed.
    """

    regs = case_registers(form, is_comparison, element_bits, machine)
    b_group = regs.b
    x_dest = regs.x_dest
    result_reg = regs.comparison_result

    typed_regs = {0}
    if form is not ElementwiseForm.UNARY_ABS:
        typed_regs.add(b_group)
    if form in (ElementwiseForm.BINARY_X, ElementwiseForm.TERNARY_X) or is_comparison:
        typed_regs.add(x_dest)
    if is_comparison:
        assert result_reg is not None
        typed_regs.discard(result_reg)

    if is_comparison:
        # The scalar form reads its scalar last, and writes the X destination.
        if form is ElementwiseForm.BINARY_X:
            plan = CasePlan(
                operands=(
                    Operand("lhs", "t1", ZERO),
                    Operand("rhs", "t2", f"m{b_group}"),
                    Operand("lhs", "t4"),
                ),
                dest=SCALAR_DEST,
                sources=(SCALAR, f"m{b_group}"),
            )
        else:
            plan = CasePlan(
                operands=(
                    Operand("lhs", "t1", ZERO),
                    Operand("rhs", "t2", f"m{b_group}"),
                ),
                dest=f"m{result_reg}",
                sources=(ZERO, f"m{b_group}"),
            )
    else:
        plan = SPECIAL_PLANS[form]
    return SpecialShape(
        plan=plan, typed_regs=tuple(sorted(typed_regs)), result_reg=result_reg
    )


def float_special_case_lines(
    case: FloatSpecialCase,
    role: FloatSpecialRole,
    form: ElementwiseForm,
    mnemonic: str,
    dtype_name: str,
    element_bits: int,
    case_number: int,
    machine: MachineConfig,
) -> list[str]:
    """The ``.text`` block of one special-value case."""

    shape = special_shape(form, role.is_comparison, element_bits, machine)
    lines = [
        f"    # special case {case_number}: {mnemonic} {dtype_name}",
        f"    li      t0, {dtype_name}",
        *[f"    msettyp m{reg}, t0" for reg in shape.typed_regs],
        "    csrw    amefflags, x0",
    ]
    if form is ElementwiseForm.BINARY_X:
        lines.append("    csrw    amestype, t0")
    if shape.result_reg is not None:
        lines.extend(
            [
                f"    li      t0, {float_comparison_result_dtype(element_bits)}",
                f"    msettyp m{shape.result_reg}, t0",
            ]
        )
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


def float_special_case_data(
    case: FloatSpecialCase, form: ElementwiseForm, element_bits: int, machine: MachineConfig
) -> list[str]:
    """The operand and expected squares of one special-value case."""

    squares = case.squares
    values = case.operands
    unary = form is ElementwiseForm.UNARY_ABS
    data = [
        *repeated_square_lines(
            squares["value"] if unary else squares["lhs"],
            values["value"] if unary else values["lhs"],
            element_bits,
            machine,
        ),
        *repeated_square_lines(squares["rhs"], values["rhs"], element_bits, machine),
        *repeated_square_lines(
            squares["expected"], case.expected, element_bits, machine
        ),
        "",
    ]
    return data


__all__ = [
    "NO_INFINITY_DTYPES",
    "FloatSpecialCase",
    "FloatSpecialRole",
    "float_special_case_data",
    "float_special_case_lines",
    "float_special_cases",
]
