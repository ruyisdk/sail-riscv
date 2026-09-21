#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""The softfloat rounding-mode recipe: overflow, underflow, and ties.

Each arithmetic instruction is swept over the six rounding modes.  The overflow
block runs an operation whose exact result exceeds the format maximum, once per
input sign (except for the absolute difference, which is unsigned by nature), and
requires the invalid and inexact flags plus the mode's saturation value.  The
role decides both the operand vector and whether the result keeps or flips the
input sign, so the same nine roles that drive the invalid-operation recipe drive
this one.
"""

from __future__ import annotations

DOC_ZH = """\
软浮点舍入模式配方：上溢、下溢与半值。

每条算术指令都在六种舍入模式上扫描。上溢块执行精确结果超过格式最大值的运算，按输入符号各一次（绝对差本质无符号，除外），并要求 invalid 与 inexact 标志加上该模式的饱和值。角色同时决定操作数向量以及结果保留还是翻转输入符号，因此驱动无效运算配方的同九个角色也驱动这一个。
"""

from typing import NamedTuple

from fp_semantics import (
    FFLAGS_OF_NX,
    FFLAGS_UF_NX,
    FLOAT_BOUNDARIES,
    ROUNDING_MODES,
    overflow_result,
    signed,
    tie_result,
    underflow_result,
)

from mmul_gen.asm import check_dst_lines, repeated_square_lines
from mmul_gen.machine import MachineConfig, dtype_stem
from mmul_gen.templates.elementwise_float_rounding_plans import (
    overflow_plan,
    tie_plan,
    underflow_plan,
)
from mmul_gen.registers import choose_distinct_m_group_bases
from mmul_gen.templates.elementwise_float_arithmetic import FloatArithmeticRole
from mmul_gen.templates.elementwise_forms import ElementwiseForm
from mmul_gen.templates.elementwise_emit import (
    plan_lines,
    x_dest_reg,
)




class RoundingOperands(NamedTuple):
    """The encoded boundary operands the rounding sweep cycles through."""

    max_pos: int
    max_neg: int
    zero: int
    two: int
    half: int
    half_ulp: int
    one: int
    one_ulp: int
    min_sub_pos: int
    min_sub_neg: int

    def square_label(self, prefix: str, name: str) -> str:
        return f"{prefix}{name}_square"


def rounding_operands(dtype_name: str, element_bits: int) -> RoundingOperands:
    """The boundary operands of one datatype, with both maximum signs."""

    values = FLOAT_BOUNDARIES[dtype_name]
    return RoundingOperands(
        max_pos=values["max"],
        max_neg=signed(values["max"], element_bits, True),
        zero=values["zero"],
        two=values["two"],
        half=values["half"],
        half_ulp=values["half_ulp"],
        one=values["one"],
        one_ulp=values["one_ulp"],
        min_sub_pos=values["min_subnormal"],
        min_sub_neg=signed(values["min_subnormal"], element_bits, True),
    )


def rounding_labels(case_number: int, dtype_name: str, operands: RoundingOperands) -> dict[str, str]:
    """The private square label of every rounding operand."""

    prefix = f"case_round{case_number}_{dtype_stem(dtype_name)}_"
    return {name: operands.square_label(prefix, name) for name in operands._fields}


def rounding_setup_lines(
    dtype_name: str,
    mode_dtype: str,
    element_bits: int,
    *,
    include_ternary_source: bool,
    x_form: bool,
    machine: MachineConfig,
) -> list[str]:
    """Round-trip the accumulator through release/acquire, then set the mode."""

    b_reg = machine.nregs(element_bits)
    typed_regs = {0, b_reg}
    if x_form:
        typed_regs.add(x_dest_reg(element_bits, machine))
    if include_ternary_source:
        _dest_reg, _src1_reg, src2_reg = choose_distinct_m_group_bases(
            machine.num_m_regs, element_bits, machine, (0, b_reg, 2 * b_reg)
        )
        typed_regs.add(src2_reg)
    lines = [
        "    ame.release",
        "    li      t0, 0",
        "    ame.acquire t1, t0",
        "    EXPECT  t1, 1",
        f"    li      t0, {dtype_name} | {mode_dtype}",
    ]
    if x_form:
        lines.append("    csrw    ame_scalar_dtype, t0")
    lines.extend(f"    msettyp m{reg}, t0" for reg in sorted(typed_regs))
    return lines




def emit_rounding_overflow_operation(
    role: FloatArithmeticRole,
    form: ElementwiseForm,
    mnemonic: str,
    labels: dict[str, str],
    element_bits: int,
    input_negative: bool,
    machine: MachineConfig,
) -> tuple[list[str], bool]:
    """The operation that overflows the format, and whether its result is negative.

    The exact result is chosen to exceed the maximum: max + max, max - (-max),
    max * 2, or an accumulator plus such a product.  A negating role flips the
    result sign relative to the input sign.
    """

    output_negative = input_negative
    if role.negates_result:
        output_negative = not output_negative
    if role.always_positive_overflow:
        output_negative = False
    return (
        plan_lines(
            overflow_plan(role, form, input_negative, element_bits, machine),
            mnemonic,
            labels,
            None,
            element_bits,
            machine,
            store=False,
        ),
        output_negative,
    )


def rounding_overflow_block(
    role: FloatArithmeticRole,
    form: ElementwiseForm,
    mnemonic: str,
    dtype_name: str,
    element_bits: int,
    case_number: int,
    machine: MachineConfig,
) -> tuple[list[str], list[str]]:
    """The whole overflow sweep: one case per sign and rounding mode."""

    operands = rounding_operands(dtype_name, element_bits)
    labels = rounding_labels(case_number, dtype_name, operands)
    signs = (False,) if role.always_positive_overflow else (False, True)
    lines: list[str] = []
    for negative in signs:
        sign_name = "negative" if negative else "positive"
        for mode_name, mode_dtype in ROUNDING_MODES:
            operation_lines, result_negative = emit_rounding_overflow_operation(
                role, form, mnemonic, labels, element_bits, negative, machine
            )
            expected = overflow_result(
                dtype_name, element_bits, mode_name, result_negative
            )
            lines.extend(
                [
                    f"    # rounding overflow: {mnemonic} {dtype_name} {sign_name} {mode_name}",
                    *rounding_setup_lines(
                        dtype_name,
                        mode_dtype,
                        element_bits,
                        include_ternary_source=form is ElementwiseForm.TERNARY_M,
                        x_form=form
                        in (ElementwiseForm.BINARY_X, ElementwiseForm.TERNARY_X),
                        machine=machine,
                    ),
                    *operation_lines,
                    "    csrr    t4, amefflags",
                    f"    EXPECT  t4, {FFLAGS_OF_NX}",
                    "    la      t3, dst_square",
                    f"    mss.rm     m{x_dest_reg(element_bits, machine) if form in (ElementwiseForm.BINARY_X, ElementwiseForm.TERNARY_X) else 0}, t3",
                    *check_dst_lines(expected, element_bits, machine=machine),
                ]
            )
    return lines, []





def _rounding_case_header(
    kind: str,
    mnemonic: str,
    dtype_name: str,
    sign_name: str,
    mode_name: str,
) -> str:
    return f"    # rounding {kind}: {mnemonic} {dtype_name} {sign_name} {mode_name}"


def rounding_underflow_block(
    role: FloatArithmeticRole,
    form: ElementwiseForm,
    mnemonic: str,
    dtype_name: str,
    element_bits: int,
    case_number: int,
    machine: MachineConfig,
) -> tuple[list[str], list[str]]:
    """The underflow sweep: the smallest subnormal times one half.

    The exact result is half of the smallest subnormal, so it rounds to zero or
    to that subnormal depending on the mode, and the sign follows the input
    unless the role negates it.
    """

    if not role.multiplies:
        return [], []
    operands = rounding_operands(dtype_name, element_bits)
    labels = rounding_labels(case_number, dtype_name, operands)
    x_dest = x_dest_reg(element_bits, machine)
    wide = form in (ElementwiseForm.BINARY_X, ElementwiseForm.TERNARY_X)
    dest_reg = x_dest if wide else 0
    lines: list[str] = []
    for negative in (False, True):
        sign_name = "negative" if negative else "positive"
        for mode_name, mode_dtype in ROUNDING_MODES:
            result_negative = not negative if role.negates_result else negative
            expected = underflow_result(
                dtype_name, element_bits, mode_name, result_negative
            )
            operation_lines = plan_lines(
                underflow_plan(role, form, negative, element_bits, machine),
                mnemonic,
                labels,
                None,
                element_bits,
                machine,
                store=False,
            )
            lines.extend(
                [
                    _rounding_case_header(
                        "underflow", mnemonic, dtype_name, sign_name, mode_name
                    ),
                    *rounding_setup_lines(
                        dtype_name,
                        mode_dtype,
                        element_bits,
                        include_ternary_source=form is ElementwiseForm.TERNARY_M,
                        x_form=wide,
                        machine=machine,
                    ),
                    *operation_lines,
                    "    csrr    t4, amefflags",
                    f"    EXPECT  t4, {FFLAGS_UF_NX}",
                    "    la      t3, dst_square",
                    f"    mss.rm     m{dest_reg}, t3",
                    *check_dst_lines(expected, element_bits, machine=machine),
                ]
            )
    return lines, []


def rounding_tie_block(
    role: FloatArithmeticRole,
    form: ElementwiseForm,
    mnemonic: str,
    dtype_name: str,
    element_bits: int,
    case_number: int,
    machine: MachineConfig,
) -> tuple[list[str], list[str]]:
    """The halfway sweep: a lower neighbour plus exactly half an ulp.

    The two lower neighbours have opposite parity, so one rounds up and one
    rounds down under the even and odd rules; only the inexact flag is raised.
    """

    # The halfway sweep exists only in the matrix forms: it covers `madd.ew`
    # and `mmulacc.ew`, not their scalar forms.
    if not role.has_halfway_case or form.takes_scalar:
        return [], []
    operands = rounding_operands(dtype_name, element_bits)
    labels = rounding_labels(case_number, dtype_name, operands)
    lines: list[str] = []
    for lower_key in ("one", "one_ulp"):
        lower = FLOAT_BOUNDARIES[dtype_name][lower_key]
        parity = "even" if lower & 1 == 0 else "odd"
        for mode_name, mode_dtype in ROUNDING_MODES:
            operation_lines = plan_lines(
                tie_plan(role, lower_key, element_bits, machine),
                mnemonic,
                labels,
                None,
                element_bits,
                machine,
                store=False,
            )
            lines.extend(
                [
                    f"    # halfway rounding: {mnemonic} {dtype_name} {parity}-lower {mode_name}",
                    *rounding_setup_lines(
                        dtype_name,
                        mode_dtype,
                        element_bits,
                        include_ternary_source=form is ElementwiseForm.TERNARY_M,
                        x_form=False,
                        machine=machine,
                    ),
                    *operation_lines,
                    "    csrr    t4, amefflags",
                    "    EXPECT  t4, 1",
                    "    la      t3, dst_square",
                    "    mss.rm     m0, t3",
                    *check_dst_lines(
                        tie_result(lower, mode_name), element_bits, machine=machine
                    ),
                ]
            )
    return lines, []


def rounding_case_lines(
    role: FloatArithmeticRole,
    form: ElementwiseForm,
    mnemonic: str,
    dtype_name: str,
    element_bits: int,
    case_number: int,
    machine: MachineConfig,
) -> tuple[list[str], list[str]]:
    """The whole rounding template for one instruction and datatype.

    The operand squares come first, then the overflow sweep and, for the roles
    that have them, the underflow and halfway sweeps.
    """

    operands = rounding_operands(dtype_name, element_bits)
    labels = rounding_labels(case_number, dtype_name, operands)
    data_lines: list[str] = []
    for name, label in labels.items():
        data_lines.extend(
            repeated_square_lines(
                label, getattr(operands, name), element_bits, machine
            )
        )
    data_lines.append("")
    lines: list[str] = []
    for block in (
        rounding_overflow_block,
        rounding_underflow_block,
        rounding_tie_block,
    ):
        block_lines, block_data = block(
            role, form, mnemonic, dtype_name, element_bits, case_number, machine
        )
        lines.extend(block_lines)
        data_lines.extend(block_data)
    return lines, data_lines


__all__ = [
    "RoundingOperands",
    "rounding_case_lines",
    "emit_rounding_overflow_operation",
    "rounding_labels",
    "rounding_operands",
    "rounding_overflow_block",
    "rounding_setup_lines",
    "rounding_tie_block",
    "rounding_underflow_block",
]
