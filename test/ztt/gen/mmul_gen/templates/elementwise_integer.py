#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""The integer elementwise recipe: one operand rule set, six operand forms.

Every elementwise instruction runs this recipe, because it is where the integer
semantics live; the form decides how the operands reach the instruction and
which square carries the power-of-two sweep.  The recipe emits each case's four
squares unconditionally -- the unused ones still document the operand layout --
and checks the destination either element by element (sweep) or as a whole.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from collections.abc import Sequence
from typing import TYPE_CHECKING

from mmul_gen.asm import (
    check_dst_element_lines,
    check_dst_lines,
    data_element_lines,
    hex_value,
    pack_nibbles,
    repeated_square_lines,
)
from mmul_gen.inputs import (
    SMALL_VALUES,
    IntegerInputCase,
    int_operands_for_case,
    power_of_two_sequence,
)
from mmul_gen.machine import MachineConfig
from mmul_gen.templates.elementwise_elements import IntegerElements
from mmul_gen.templates.elementwise_expected import integer_expected
from collections.abc import Callable
from functools import partial
from typing import Any

from mmul_gen.templates.elementwise_emit import (
    EW_X_DEST_REG,
    EW_X_SRC_REG,
    SCALAR,
    SCALAR_DEST,
    SOURCE,
    ZERO,
    CasePlan,
    Operand,
    plan_for,
    plan_lines,
    vector_operands,
    x_dest_reg,
)
from mmul_gen.templates.elementwise_forms import ElementwiseForm

if TYPE_CHECKING:
    from mmul_gen.instructions.elementwise.base import ElementwiseInstruction

#: Which square carries the power-of-two sweep, per form.
INTEGER_SEQUENCE_SQUARE_ROLE = {
    ElementwiseForm.BINARY_M: "a",
    ElementwiseForm.BINARY_X: "b",
    ElementwiseForm.TERNARY_M: "a",
    ElementwiseForm.TERNARY_X: "b",
    ElementwiseForm.MOVE_M: "b",
    ElementwiseForm.UNARY_ABS: "abs",
}

#: The four squares every integer case lays out, in emission order.
SQUARE_ROLES = ("a", "b", "dest", "abs")


def case_fits_m_registers(
    form: ElementwiseForm, element_bits: int, machine: MachineConfig, *, floating: bool = False
) -> bool:
    """Whether one case has enough independent M-register groups."""

    nregs = machine.nregs(element_bits)
    if form in (
        ElementwiseForm.BINARY_M,
        ElementwiseForm.BINARY_X,
        ElementwiseForm.TERNARY_X,
        ElementwiseForm.MOVE_M,
    ):
        groups = 2
    elif form is ElementwiseForm.TERNARY_M:
        # The integer ternary template reuses one source group for A and B;
        # the floating templates deliberately keep all three distinct.
        groups = 3 if floating else 2
    else:
        groups = 1
    return groups * nregs <= machine.num_m_regs


def type_setup_lines(
    dtype_name: str,
    element_bits: int,
    machine: MachineConfig,
    *,
    include_x_dest: bool,
    include_source: bool,
) -> list[str]:
    """Type the descriptor into every M register the case will touch."""

    b_reg = machine.nregs(element_bits)
    typed_regs = {0}
    if include_source:
        typed_regs.add(b_reg)
    if include_x_dest:
        typed_regs.add(x_dest_reg(element_bits, machine))
    lines = [f"    li      t0, {dtype_name}"]
    lines.extend(f"    msettyp m{reg}, t0" for reg in sorted(typed_regs))
    lines.append("")
    return lines


def sequence_square_lines(
    label: str, values: Sequence[int], element_bits: int, machine: MachineConfig
) -> list[str]:
    """One square whose elements cycle through ``values``."""

    if not values:
        raise ValueError("sequence square needs at least one value")
    cycled = [
        values[index % len(values)]
        for index in range(machine.storage_elements(element_bits))
    ]
    lines = [f".balign {machine.square_bytes(element_bits)}", f"{label}:"]
    if element_bits == 4:
        packed = ", ".join(hex_value(value, 8) for value in pack_nibbles(cycled))
        lines.append(f"    .byte {packed}")
        return lines
    lines.extend(data_element_lines(cycled, element_bits))
    return lines


#: The formula an integer template computes its expectations with: the
#: instruction's own ``evaluate``, called with the instruction as its receiver.
ElementwiseFormula = Callable[[Any, IntegerElements], int]


def integer_cases(
    instruction: "ElementwiseInstruction",
    inputs: tuple[IntegerInputCase, ...],
    evaluate: ElementwiseFormula,
    dtype_name: str,
    element_bits: int,
    machine: MachineConfig,
    *,
    wide: bool,
) -> tuple[IntegerCase, ...]:
    """Build the integer cases of one (instruction, datatype) point.

    ``inputs`` and ``evaluate`` are what the instruction handed the integer template:
    its own input inventory, composed from the family's universal cases plus its
    overflow case if it has one, and its own formula for what it computes.  The
    input cases only decide which operands the formula sees.  The 128-bit template narrows a scalar form to the small
    case, because a scalar travels through an XLEN register and cannot carry a
    wide operand.  The power-of-two case is the one case whose expectation is a
    sweep rather than a single value.
    """

    form = instruction.form
    cases = (SMALL_VALUES,) if wide and form.takes_scalar else inputs
    built: list[IntegerCase] = []
    for input_case in cases:
        values = int_operands_for_case(input_case, dtype_name, element_bits)
        operands = IntegerOperands(
            a=values["a"],
            b=values["b"],
            scalar=values["scalar"],
            dest=values["dest"],
            abs=values["abs"],
        )
        if input_case.category != "power_of_two":
            built.append(
                IntegerCase(
                    operands=operands,
                    expected=integer_expected(
                        partial(evaluate, instruction),
                        form,
                        dtype_name,
                        element_bits,
                        values,
                    ),
                    tag=input_case.name,
                    description=input_case.description,
                )
            )
            continue
        sequence = power_of_two_sequence(
            element_bits, machine.storage_elements(element_bits)
        )
        # The sweep moves one square through the encoded powers of two; every
        # other operand keeps the value the case gave it.
        swept_square = INTEGER_SEQUENCE_SQUARE_ROLE[form]
        built.append(
            IntegerCase(
                operands=operands,
                tag=input_case.name,
                description=input_case.description,
                sweep=(
                    tuple(sequence),
                    tuple(
                        integer_expected(
                            partial(evaluate, instruction),
                            form,
                            dtype_name,
                            element_bits,
                            {**values, swept_square: raw},
                        )
                        for raw in sequence
                    ),
                ),
            )
        )
    return tuple(built)


@dataclass(frozen=True)
class IntegerOperands:
    """The four operand squares of one integer case."""

    a: int
    b: int
    scalar: int
    dest: int
    abs: int

    def square_value(self, role: str) -> int:
        return {
            "a": self.a,
            "b": self.b,
            "dest": self.dest,
            "abs": self.abs,
        }[role]


@dataclass(frozen=True)
class IntegerCase:
    """One decided integer case: its operands, its answer, and its review tag."""

    operands: IntegerOperands
    expected: int | None = None
    tag: str | None = None
    description: str | None = None
    #: ``(encoded powers of two, expected elements)`` when the case sweeps.
    sweep: tuple[tuple[int, ...], tuple[int, ...]] | None = None
    squares: dict[str, str] = field(default_factory=dict)

    def labelled(self, label_prefix: str) -> "IntegerCase":
        """Attach the private square labels of one emitted case."""

        return IntegerCase(
            operands=self.operands,
            expected=self.expected,
            tag=self.tag,
            description=self.description,
            sweep=self.sweep,
            squares={
                role: f"{label_prefix}{role}_square" for role in SQUARE_ROLES
            },
        )


#: What each form loads and stores.  The scalar forms put their source group at
#: register 0 (``EW_X_SRC_REG``), which is why their loads name :data:`ZERO`.  The
#: integer recipe materialises its scalar in decimal, the floating recipes in hex.
INTEGER_PLANS: dict[ElementwiseForm, CasePlan] = {
    ElementwiseForm.BINARY_M: CasePlan(
        vector_operands("a", "b"), ZERO, (ZERO, SOURCE)
    ),
    ElementwiseForm.BINARY_X: CasePlan(
        (Operand("scalar", "t4", source="decimal"), Operand("b", "t2", ZERO)),
        SCALAR_DEST,
        (SCALAR, ZERO),
    ),
    # The integer ternary form reuses one source group for both operands.
    ElementwiseForm.TERNARY_M: CasePlan(
        vector_operands("a", "b"), ZERO, (ZERO, SOURCE)
    ),
    ElementwiseForm.TERNARY_X: CasePlan(
        (
            Operand("dest", "t1", SCALAR_DEST),
            Operand("b", "t2", ZERO),
            Operand("scalar", "t4", source="decimal"),
        ),
        SCALAR_DEST,
        (SCALAR, ZERO),
    ),
    ElementwiseForm.MOVE_M: CasePlan((Operand("b", "t2", SOURCE),), ZERO, (SOURCE,)),
    ElementwiseForm.UNARY_ABS: CasePlan((Operand("abs", "t1", ZERO),), ZERO, (ZERO,)),
}


#: The forms whose case carries its operand comment; the move and absolute-value
#: forms emit none.
COMMENTED_FORMS = (
    ElementwiseForm.BINARY_M,
    ElementwiseForm.BINARY_X,
    ElementwiseForm.TERNARY_M,
    ElementwiseForm.TERNARY_X,
)


def operand_value(operands: IntegerOperands, role: str) -> int:
    """The value of one planned operand; the scalar has no square of its own."""

    return operands.scalar if role == "scalar" else operands.square_value(role)


def integer_case_lines(
    case: IntegerCase,
    form: ElementwiseForm,
    mnemonic: str,
    dtype_name: str,
    element_bits: int,
    case_number: int,
    machine: MachineConfig,
) -> list[str]:
    """The ``.text`` block of one integer case.

    The case number is the source-wide case counter, so the ``# case N`` comment
    and the private square labels stay in step with the rest of the file.
    """

    values = case.operands
    rule_tag = f" [{case.tag}]" if case.tag else ""
    sweep_comment = (
        f"    # {mnemonic}: sweep {len(case.sweep[0])} "
        f"encoded powers of two, B={values.b}"
        if case.sweep is not None
        else None
    )
    form_comment = {
        ElementwiseForm.BINARY_M: f"    # {mnemonic}: A={values.a}, B={values.b}",
        ElementwiseForm.BINARY_X: f"    # {mnemonic}: scalar={values.scalar}, B={values.b}",
        ElementwiseForm.TERNARY_M: f"    # {mnemonic}: D/A={values.a}, B={values.b}",
        ElementwiseForm.TERNARY_X: (
            f"    # {mnemonic}: D={values.dest}, scalar={values.scalar}, B={values.b}"
        ),
    }.get(form)
    comment = sweep_comment if sweep_comment is not None else form_comment

    lines = [f"    # case {case_number}: {mnemonic} {dtype_name}{rule_tag}"]
    lines.extend(
        type_setup_lines(
            dtype_name,
            element_bits,
            machine,
            include_x_dest=form in (ElementwiseForm.BINARY_X, ElementwiseForm.TERNARY_X),
            include_source=form is not ElementwiseForm.UNARY_ABS,
        )
    )
    if form in (ElementwiseForm.BINARY_X, ElementwiseForm.TERNARY_X):
        lines.insert(-1, "    csrw    amestype, t0")
    if case.description:
        # The case description is echoed here as well as by the driver above the
        # layout comment, so the input label sits next to the operands.
        lines.append(f"    # input: {case.description}")

    if comment is not None and form in COMMENTED_FORMS:
        lines.append(comment)
    lines.extend(
        plan_lines(
            plan_for(form, INTEGER_PLANS, "elementwise instruction form"),
            mnemonic,
            case.squares,
            lambda role: operand_value(values, role),
            element_bits,
            machine,
        )
    )

    if case.sweep is not None:
        for index, sweep_element in enumerate(case.sweep[1]):
            lines.extend(check_dst_element_lines(sweep_element, element_bits, index))
    else:
        if case.expected is None:
            raise ValueError(f"{mnemonic}: a non-sweep case needs an expected value")
        lines.extend(check_dst_lines(case.expected, element_bits, machine=machine))
    return lines


def integer_case_data(
    case: IntegerCase, form: ElementwiseForm, element_bits: int, machine: MachineConfig
) -> list[str]:
    """The ``.data`` blocks of one integer case: its four operand squares."""

    sequence_role = (
        INTEGER_SEQUENCE_SQUARE_ROLE.get(form) if case.sweep is not None else None
    )
    data: list[str] = []
    for role in SQUARE_ROLES:
        label = case.squares[role]
        if role == sequence_role:
            assert case.sweep is not None
            data.extend(
                sequence_square_lines(label, list(case.sweep[0]), element_bits, machine)
            )
            continue
        data.extend(
            repeated_square_lines(
                label, case.operands.square_value(role), element_bits, machine
            )
        )
    return data


__all__ = [
    "EW_X_DEST_REG",
    "EW_X_SRC_REG",
    "INTEGER_SEQUENCE_SQUARE_ROLE",
    "SQUARE_ROLES",
    "IntegerCase",
    "IntegerOperands",
    "case_fits_m_registers",
    "integer_case_data",
    "integer_case_lines",
    "integer_cases",
    "sequence_square_lines",
    "type_setup_lines",
    "x_dest_reg",
]
