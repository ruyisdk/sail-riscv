#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""The softfloat elementwise recipe: nominal operands, one case per datatype.

Each softfloat datatype has its own nominal operand tuple (the same nominal
values in that format), and the instruction declares what its answer is with its
own ``evaluate_float``: an operand of the model's roster, or -- for a comparison
-- the mask of the outcome.  A comparison additionally seeds its destination with
the *opposite* result, so a passing test proves the instruction wrote the
destination rather than leaving it alone.

The model itself is read in exactly one place (``FLOAT_OPERATION_VALUES``),
because a softfloat answer is a property of the format and the operation, not
something an instruction computes.
"""

from __future__ import annotations

DOC_ZH = """\
软浮点 elementwise 配方：标称操作数，每个 datatype 一个用例。

每个软浮点 datatype 都有自己的标称操作数元组（同一格式下的同一组标称值），指令用自己的 ``evaluate_float`` 声明它的答案：模型名册中的一个操作数，或者（比较类）结果的掩码。比较类还会用*相反*的结果给目的方阵播种，因此通过的测试证明指令确实写入了目的方阵，而不是置之不理。

模型本身只在一处读取（``FLOAT_OPERATION_VALUES``），因为软浮点答案是格式与操作的属性，不是指令计算出来的。
"""

from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import Any

from fp_semantics import FLOAT_OPERATION_VALUES

from mmul_gen.asm import check_dst_lines, repeated_square_lines
from mmul_gen.machine import MachineConfig
from mmul_gen.registers import choose_distinct_m_group_bases
from mmul_gen.templates.elementwise_forms import ElementwiseForm
from mmul_gen.templates.elementwise_emit import (
    SCALAR,
    SCALAR_DEST,
    SOURCE,
    ZERO,
    CasePlan,
    Operand,
    plan_lines,
    x_dest_reg,
)

#: Operand squares every softfloat case lays out, in emission order.
FLOAT_ROLES = ("a", "b", "dest", "neg_abs")


#: The formula a softfloat template computes its expectation with: the
#: instruction's own ``evaluate_float``, called with the instruction as its
#: receiver and given the datatype name and element width.  What the body does is
#: the instruction's business -- most read one entry of the model's roster, a
#: comparison returns its mask -- and a comparison also declares itself with
#: ``ElementwiseFloatNominal(..., comparison=True)``, because only the template can
#: see the destination seeding and the three-M-group rule that go with it.
FloatFormula = Callable[[Any, str, int], int]


@dataclass(frozen=True)
class FloatCase:
    """One nominal softfloat case: its operands, its answer, and its labels."""

    values: dict[str, int]
    expected: int
    is_comparison: bool
    squares: dict[str, str]

    def labelled(self, label_prefix: str) -> "FloatCase":
        squares = {role: f"{label_prefix}{role}_square" for role in FLOAT_ROLES}
        squares["comparison_dest"] = f"{label_prefix}comparison_dest_square"
        return FloatCase(
            values=self.values,
            expected=self.expected,
            is_comparison=self.is_comparison,
            squares=squares,
        )


def float_comparison_result_dtype(element_bits: int) -> str:
    """A comparison yields an unsigned integer of the element width."""

    return f"AME_UINT{element_bits}_DTYPE"


def float_case(
    evaluate: Callable[[str, int], int],
    comparison: bool,
    dtype_name: str,
    element_bits: int,
) -> FloatCase:
    """Build the nominal case of one (instruction, datatype) point.

    ``evaluate`` is the instruction's ``evaluate_float``, already bound to it, so
    the case builder asks for the answer instead of deriving it.  ``comparison``
    is the one part of that answer a function cannot carry: a comparison seeds
    its destination with the opposite result, so the template has to say so.
    """

    values = dict(FLOAT_OPERATION_VALUES[dtype_name])
    expected = evaluate(dtype_name, element_bits)
    # A comparison seeds the destination with the opposite answer.
    values["comparison_initial"] = 0 if expected else (1 << element_bits) - 1
    return FloatCase(
        values=values,
        expected=expected,
        is_comparison=comparison,
        squares={},
    )


#: The operand comment each form prints above its loads; the unary form has none.
FLOAT_COMMENTS: dict[ElementwiseForm, str] = {
    ElementwiseForm.BINARY_M: "A=1.5f, B=2.0f",
    ElementwiseForm.BINARY_X: "scalar=4.0f, B=2.0f",
    ElementwiseForm.TERNARY_M: "D=0.5f, A=1.5f, B=2.0f",
    ElementwiseForm.TERNARY_X: "D=0.5f, scalar=4.0f, B=2.0f",
}

#: The destination, sources and operand order of the forms whose registers are
#: fixed.  The ternary M form and the comparisons are built from these, because
#: which groups they may use depends on the configured M-register file.
FLOAT_PLANS: dict[ElementwiseForm, CasePlan] = {
    ElementwiseForm.BINARY_M: CasePlan(
        (Operand("a", "t1", ZERO), Operand("b", "t2", SOURCE)), ZERO, (ZERO, SOURCE)
    ),
    ElementwiseForm.BINARY_X: CasePlan(
        (Operand("scalar", "t4"), Operand("b", "t2", ZERO)),
        SCALAR_DEST,
        (SCALAR, ZERO),
    ),
    ElementwiseForm.TERNARY_X: CasePlan(
        (
            Operand("dest", "t1", SCALAR_DEST),
            Operand("b", "t2", ZERO),
            Operand("scalar", "t4"),
        ),
        SCALAR_DEST,
        (SCALAR, ZERO),
    ),
    ElementwiseForm.UNARY_ABS: CasePlan(
        (Operand("neg_abs", "t1", ZERO),), ZERO, (ZERO,)
    ),
}


@dataclass(frozen=True)
class FloatShape:
    """One softfloat case's plan and the M-register groups its header types."""

    plan: CasePlan
    typed_regs: tuple[int, ...]
    comparison_reg: int | None


@dataclass(frozen=True)
class CaseRegisters:
    """The M-register groups one softfloat case reads and writes.

    ``ternary_dest`` is the group the ternary chooser picked for the destination,
    or ``None`` for a form that does not use one.
    """

    source: int
    b: int
    x_dest: int
    ternary_src1: int
    ternary_src2: int
    ternary_dest: int | None
    comparison_result: int | None


def case_registers(
    form: ElementwiseForm,
    is_comparison: bool,
    element_bits: int,
    machine: MachineConfig,
) -> CaseRegisters:
    """The groups one softfloat case may use.

    A comparison writes a group of its own and a ternary M form reads two, so
    both need groups disjoint from m0.  Which groups are free depends on the
    configured M-register file, so every softfloat recipe asks for them here
    instead of each choosing for itself.
    """

    source = machine.nregs(element_bits)
    x_dest = x_dest_reg(element_bits, machine)
    b_group = source
    ternary_src1, ternary_src2, ternary_dest = source, 2 * source, None
    comparison_result: int | None = None
    if is_comparison:
        _src1, b_group, comparison_result = choose_distinct_m_group_bases(
            machine.num_m_regs, element_bits, machine, (0, source, x_dest)
        )
    elif form is ElementwiseForm.TERNARY_M:
        ternary_dest, ternary_src1, ternary_src2 = choose_distinct_m_group_bases(
            machine.num_m_regs, element_bits, machine, (0, source, 2 * source)
        )
    return CaseRegisters(
        source=source,
        b=b_group,
        x_dest=x_dest,
        ternary_src1=ternary_src1,
        ternary_src2=ternary_src2,
        ternary_dest=ternary_dest,
        comparison_result=comparison_result,
    )


def float_shape(
    form: ElementwiseForm,
    is_comparison: bool,
    element_bits: int,
    machine: MachineConfig,
) -> FloatShape:
    """The plan and the register set of one softfloat case.

    A comparison writes a group of its own and a ternary M form reads two, so
    both need groups disjoint from m0.  Which groups are free depends on the
    configured M-register file, so the plan is built here rather than declared as
    a constant the way the fixed forms are.
    """

    regs = case_registers(form, is_comparison, element_bits, machine)
    b_group = regs.b
    x_dest = regs.x_dest
    src1_group = regs.ternary_src1
    ternary_src2_group = regs.ternary_src2
    comparison_reg = regs.comparison_result

    typed_regs = {0}
    if form is not ElementwiseForm.UNARY_ABS:
        typed_regs.add(b_group)
    if form is ElementwiseForm.TERNARY_M:
        typed_regs.add(ternary_src2_group)
    if form in (ElementwiseForm.BINARY_X, ElementwiseForm.TERNARY_X) or is_comparison:
        typed_regs.add(x_dest)
    # Keep the intermediate comparison group typed when it fits, but never emit
    # an out-of-range register on a smaller M-register file.
    if is_comparison and 3 * b_group <= machine.num_m_regs:
        typed_regs.add(2 * b_group)
    if is_comparison:
        assert comparison_reg is not None
        typed_regs.discard(comparison_reg)

    if form is ElementwiseForm.TERNARY_M:
        plan = CasePlan(
            operands=(
                Operand("dest", "t1", ZERO),
                Operand("a", "t1", f"m{src1_group}"),
                Operand("b", "t2", f"m{ternary_src2_group}"),
            ),
            dest=ZERO,
            sources=(f"m{src1_group}", f"m{ternary_src2_group}"),
        )
    else:
        plan = FLOAT_PLANS[form]
    if is_comparison:
        if form is ElementwiseForm.BINARY_M:
            plan = CasePlan(
                operands=(
                    Operand("a", "t1", ZERO),
                    Operand("b", "t2", f"m{b_group}"),
                ),
                dest=f"m{comparison_reg}",
                sources=(ZERO, f"m{b_group}"),
            )
        # A comparison plants the opposite answer in the group it will write.
        plan = replace(plan, seed=Operand("comparison_dest", "t3", plan.dest))
    return FloatShape(
        plan=plan, typed_regs=tuple(sorted(typed_regs)), comparison_reg=comparison_reg
    )


def float_case_lines(
    case: FloatCase,
    form: ElementwiseForm,
    mnemonic: str,
    dtype_name: str,
    element_bits: int,
    case_number: int,
    machine: MachineConfig,
) -> list[str]:
    """The ``.text`` block of one nominal softfloat case."""

    shape = float_shape(form, case.is_comparison, element_bits, machine)
    lines = [
        f"    # case {case_number}: {mnemonic} {dtype_name}",
        f"    li      t0, {dtype_name}",
        *[f"    msettyp m{reg}, t0" for reg in shape.typed_regs],
    ]
    if form in (ElementwiseForm.BINARY_X, ElementwiseForm.TERNARY_X):
        lines.append("    csrw    ame_scalar_dtype, t0")
    if shape.comparison_reg is not None:
        lines.extend(
            [
                f"    li      t0, {float_comparison_result_dtype(element_bits)}",
                f"    msettyp m{shape.comparison_reg}, t0",
            ]
        )
    lines.append("")
    comment = FLOAT_COMMENTS.get(form)
    if comment is not None:
        lines.append(f"    # {mnemonic}: {comment}")
    lines.extend(
        plan_lines(
            shape.plan,
            mnemonic,
            case.squares,
            lambda role: case.values[role],
            element_bits,
            machine,
        )
    )
    lines.extend(check_dst_lines(case.expected, element_bits, machine=machine))
    return lines


def float_case_data(
    case: FloatCase, element_bits: int, machine: MachineConfig
) -> list[str]:
    """The operand squares of one nominal softfloat case."""

    squares = case.squares
    data: list[str] = []
    for label, key in (
        (squares["a"], "a"),
        (squares["b"], "b"),
        (squares["dest"], "dest"),
        (squares["neg_abs"], "neg_abs"),
    ):
        data.extend(
            repeated_square_lines(label, case.values[key], element_bits, machine)
        )
    if case.is_comparison:
        data.extend(
            repeated_square_lines(
                squares["comparison_dest"],
                case.values["comparison_initial"],
                element_bits,
                machine,
            )
        )
    data.append("")
    return data


__all__ = [
    "FLOAT_COMMENTS",
    "FLOAT_PLANS",
    "FLOAT_ROLES",
    "CaseRegisters",
    "FloatShape",
    "case_registers",
    "float_shape",
    "FloatCase",
    "FloatFormula",
    "float_case",
    "float_case_data",
    "float_case_lines",
    "float_comparison_result_dtype",

]
