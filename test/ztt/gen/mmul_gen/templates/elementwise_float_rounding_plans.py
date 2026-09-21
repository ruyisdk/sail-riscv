#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Which data squares express each rounding case.

Every rounding sweep is driven by the same three questions -- which squares make
the result overflow, underflow, or land exactly halfway -- and each question is
answered per :class:`FloatArithmeticRole` here, so the template renderer next door
reads a plan instead of branching on the role.  The answers are label roles, not
labels: the template decides which squares back them.
"""

from __future__ import annotations

DOC_ZH = """\
哪些数据方阵表达每个舍入用例。

每次舍入扫描都由同样的三个问题驱动——哪些方阵使结果上溢、下溢或恰好落在半值——每个问题在这里按 :class:`FloatArithmeticRole` 回答，因此隔壁的模板渲染器读取计划，而不是按角色分支。答案给出的是标签角色而不是标签：由模板决定用哪些方阵来承载。
"""

from mmul_gen.machine import MachineConfig
from mmul_gen.templates.elementwise_float import case_registers
from mmul_gen.templates.elementwise_float_arithmetic import FloatArithmeticRole
from mmul_gen.templates.elementwise_emit import (
    SCALAR,
    SCALAR_DEST,
    SOURCE,
    ZERO,
    CasePlan,
    Operand,
)
from mmul_gen.templates.elementwise_forms import ElementwiseForm


def overflow_operands(
    role: FloatArithmeticRole, input_negative: bool
) -> tuple[str, str]:
    """The two squares that drive one role past the format maximum.

    An add, a subtract and a multiply all land on the maximum itself, and
    reaching it from the negative side needs the opposite-signed maximum.  The
    absolute difference needs both maxima, and a fused multiply accumulates the
    maximum into the accumulator -- which is zero -- or the accumulator into it.
    """

    max_role = "max_neg" if input_negative else "max_pos"
    opposite_role = "max_pos" if input_negative else "max_neg"
    if role.always_positive_overflow:
        return "max_pos", "max_neg"
    if role.multiplies and not role.fused:
        return max_role, "two"
    if role.fused:
        # A fused multiply negates through its product, not through its addend.
        return (max_role, "zero") if role.addend_is_destination else ("zero", max_role)
    if role.negates_result:
        return max_role, opposite_role
    return max_role, max_role

def overflow_plan(
    role: FloatArithmeticRole,
    form: ElementwiseForm,
    input_negative: bool,
    element_bits: int,
    machine: MachineConfig,
) -> CasePlan:
    """The operand plan of one overflow operation.

    The scalar forms read the first operand out of its square into a
    general-purpose register and the ternary forms read a second M group, so
    which registers are used depends on the configured M-register file.
    """

    first_role, second_role = overflow_operands(role, input_negative)
    regs = case_registers(form, False, element_bits, machine)
    if role.fused:
        if form is ElementwiseForm.TERNARY_X:
            return CasePlan(
                operands=(
                    Operand(first_role, "t1", SCALAR_DEST),
                    Operand(second_role, "t4", source="square"),
                    Operand("two", "t2", ZERO),
                ),
                dest=SCALAR_DEST,
                sources=(SCALAR, ZERO),
            )
        if form is ElementwiseForm.TERNARY_M:
            return CasePlan(
                operands=(
                    Operand(first_role, "t1", ZERO),
                    Operand(second_role, "t1", f"m{regs.b}"),
                    Operand("two", "t2", f"m{regs.ternary_src2}"),
                ),
                dest=ZERO,
                sources=(f"m{regs.b}", f"m{regs.ternary_src2}"),
            )
        raise ValueError(f"unsupported fused rounding form: {form.value}")
    if form is ElementwiseForm.BINARY_X:
        return CasePlan(
            operands=(
                Operand(first_role, "t4", source="square"),
                Operand(second_role, "t2", ZERO),
            ),
            dest=SCALAR_DEST,
            sources=(SCALAR, ZERO),
        )
    # The matrix forms read the second operand from the group the chooser picked,
    # which is the second group unless a ternary form is in play.
    b_token = f"m{regs.b}" if form is ElementwiseForm.TERNARY_M else SOURCE
    return CasePlan(
        operands=(
            Operand(first_role, "t1", ZERO),
            Operand(second_role, "t2", b_token),
        ),
        dest=ZERO,
        sources=(ZERO, b_token),
    )

def underflow_plan(
    role: FloatArithmeticRole,
    form: ElementwiseForm,
    negative: bool,
    element_bits: int,
    machine: MachineConfig,
) -> CasePlan:
    """The operand plan of one underflow operation.

    The wide forms read their first or middle operand out of its square as a
    scalar, while the ternary M form reads its third operand from the group after
    the first source, which is the group the setup helper typed.
    """

    source_role = "min_sub_neg" if negative else "min_sub_pos"
    upper_group = f"m{2 * machine.nregs(element_bits)}"
    if not role.multiplies:
        raise ValueError(f"no underflow operation for {role.value}")
    if not role.fused:
        # The plain product multiplies the subnormal by one half.
        wide = (
            Operand(source_role, "t4", source="square"),
            Operand("half", "t2", ZERO),
        )
        plain = (Operand(source_role, "t1", ZERO), Operand("half", "t2", SOURCE))
        plain_sources = (ZERO, SOURCE)
    elif role.addend_is_destination:
        # The destination holds the subnormal, so it is the second product input.
        wide = (
            Operand("half", "t1", SCALAR_DEST),
            Operand("zero", "t4", source="square"),
            Operand(source_role, "t2", ZERO),
        )
        plain = (
            Operand("half", "t1", ZERO),
            Operand("zero", "t1", SOURCE),
            Operand(source_role, "t2", upper_group),
        )
        plain_sources = (SOURCE, upper_group)
    else:
        # The accumulator is zero, so the subnormal is the product input.
        wide = (
            Operand("zero", "t1", SCALAR_DEST),
            Operand(source_role, "t4", source="square"),
            Operand("half", "t2", ZERO),
        )
        plain = (
            Operand("zero", "t1", ZERO),
            Operand(source_role, "t1", SOURCE),
            Operand("half", "t2", upper_group),
        )
        plain_sources = (SOURCE, upper_group)
    if form in (ElementwiseForm.BINARY_X, ElementwiseForm.TERNARY_X):
        return CasePlan(wide, SCALAR_DEST, (SCALAR, ZERO))
    return CasePlan(plain, ZERO, plain_sources)

def tie_plan(
    role: FloatArithmeticRole,
    lower_role: str,
    element_bits: int,
    machine: MachineConfig,
) -> CasePlan:
    """The operand plan of one halfway case, which exists only in matrix forms."""

    upper_group = f"m{2 * machine.nregs(element_bits)}"
    if not role.fused:
        return CasePlan(
            (Operand(lower_role, "t1", ZERO), Operand("half_ulp", "t2", SOURCE)),
            ZERO,
            (ZERO, SOURCE),
        )
    # The accumulating product adds its half ulp to the lower neighbour.
    return CasePlan(
        (
            Operand(lower_role, "t1", ZERO),
            Operand("half_ulp", "t1", SOURCE),
            Operand("one", "t2", upper_group),
        ),
        ZERO,
        (SOURCE, upper_group),
    )

__all__ = [
    "overflow_operands",
    "overflow_plan",
    "tie_plan",
    "underflow_plan",
]
