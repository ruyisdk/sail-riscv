#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""The seven elementwise templates, and what each one is given.

Each is a template that a class constructs with its own input::

    templates = (
        ElementwiseIntegerValueRules(BASE_INTEGER_INPUT_CASES),
        ElementwiseSaturatingBoundary(SaturatingExpectation.MAX, CasePlan(...)),
        ElementwiseFloatSpecialValues(FloatArithmeticRole.ADD),
    )

so the instance carries the values it checks, the list *is* the instruction's
own list of checks, and the order it is written in is the order its cases appear
in the generated file.  Each instruction's template table is thus written out in
its class body -- repeated, but read straight off that body:

* the integer value rules, then again for 128-bit datatypes;
* the saturating boundary, then again for 128-bit datatypes;
* the nominal softfloat case;
* the special values, split between the arithmetic roles and the rest;
* the rounding-mode sweep, for the arithmetic roles.

:data:`ELEMENTWISE_TEMPLATE_CLASSES` holds the seven classes in that canonical
order; the tests check every instruction's list against it, because a generated
source and the parity check depend on the order.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from functools import partial

from mmul_gen.inputs import IntegerInputCase
from mmul_gen.machine import DType, MachineConfig, dtype_stem
from mmul_gen import machine as domains
from mmul_gen.templates.base import Case, CaseOutput, Template, case_payload
from mmul_gen.templates.elementwise_float import (
    FloatCase,
    FloatFormula,
    float_case,
    float_case_data,
    float_case_lines,
)
from mmul_gen.templates.elementwise_float_arithmetic import (
    FloatArithmeticCase,
    FloatArithmeticRole,
    float_arithmetic_case_data,
    float_arithmetic_case_lines,
    float_arithmetic_cases,
)
from mmul_gen.templates.elementwise_float_rounding import (
    RoundingOperands,
    rounding_case_lines,
    rounding_operands,
)
from mmul_gen.templates.elementwise_float_special import (
    FloatSpecialCase,
    FloatSpecialRole,
    float_special_case_data,
    float_special_case_lines,
    float_special_cases,
)
from mmul_gen.templates.elementwise_integer import (
    ElementwiseFormula,
    IntegerCase,
    case_fits_m_registers,
    integer_case_data,
    integer_case_lines,
    integer_cases,
)
from mmul_gen.templates.elementwise_emit import CasePlan
from mmul_gen.templates.elementwise_saturating import (
    SaturatingCase,
    SaturatingExpectation,
    saturating_case,
    saturating_case_data,
    saturating_case_lines,
)

if TYPE_CHECKING:
    from mmul_gen.instruction import Instruction
    from mmul_gen.instructions.elementwise.base import ElementwiseInstruction


def as_elementwise(instruction: "Instruction") -> "ElementwiseInstruction":
    """Narrow to the elementwise family, failing fast on a mis-paired template.

    The framework hands a renderer a plain instruction; the elementwise templates
    read the family's own operand form, so they say so once instead of
    suppressing the attribute access on every line that uses it.
    """

    from mmul_gen.instructions.elementwise.base import ElementwiseInstruction

    if not isinstance(instruction, ElementwiseInstruction):
        raise TypeError(
            f"an elementwise template was paired with {type(instruction).__name__}"
        )
    return instruction


def _integer_fits(
    machine: MachineConfig, instruction: "Instruction", dtype: DType | None
) -> bool:
    assert dtype is not None
    form = as_elementwise(instruction).form
    return case_fits_m_registers(form, dtype.bits, machine)


def _float_fits(
    machine: MachineConfig,
    instruction: "Instruction",
    dtype: DType | None,
    is_comparison: bool = False,
) -> bool:
    """Whether the configuration holds a softfloat case at all.

    A comparison also needs three independent M groups -- two sources and a
    result -- which is why the template passes its own flag in rather than having
    its renderer read it.
    """

    assert dtype is not None
    form = as_elementwise(instruction).form
    if not case_fits_m_registers(form, dtype.bits, machine, floating=True):
        return False
    return not (
        is_comparison and 3 * machine.nregs(dtype.bits) > machine.num_m_regs
    )


def comparison_declared_by(instruction: "Instruction") -> bool:
    """Whether ``instruction``'s own templates hold a comparison's nominal case.

    A comparison's answer is a mask, and the three-M-group rule the softfloat
    templates share needs to know about it.  It is read from the instruction's own
    template list rather than from a second declaration, and only the resource
    predicate reads it -- it never decides whether a template runs.
    """

    for template in instruction.templates:
        if isinstance(template, ElementwiseFloatNominal):
            return template.comparison
    return False


class ElementwiseTemplate(Template, family_base=True):
    """One elementwise template, holding what it tests.

    A template is constructed with its input -- an instruction writes
    ``ElementwiseFloatNominal(evaluate_float)`` in its ``templates`` and that
    instance carries the formula it checks.  So a template instance exists only
    where it runs, and the operand ``form`` is the one family-wide fact it still
    reads from the instruction.
    """

    def fits(self, machine, instruction, dtype=None) -> bool:
        return self.fits_resources(machine, instruction, dtype)

    def fits_resources(self, machine, instruction, dtype=None) -> bool:
        """Whether this configuration has the registers the template needs."""

        return True


class ElementwiseIntegerValueRules(ElementwiseTemplate):
    """Nominal integer operands and answers, one case per input rule."""

    name = "elementwise_integer_value_rules"
    dtypes = domains.FORMED_INTEGER

    def __init__(
        self, inputs: tuple[IntegerInputCase, ...], evaluate: ElementwiseFormula
    ) -> None:
        """``inputs`` is the inventory this template sweeps; ``evaluate`` its formula.

        The formula is the instruction's own ``evaluate``, handed over when the
        template is constructed, so the template never reaches back into the
        instruction for what to expect.
        """

        self.inputs = inputs
        self.evaluate = evaluate

    def fits_resources(self, machine, instruction, dtype=None) -> bool:
        return _integer_fits(machine, instruction, dtype)

    def build(self, machine, instruction, dtype) -> Sequence[Case]:
        instruction = as_elementwise(instruction)
        assert dtype is not None
        cases = integer_cases(
            instruction,
            self.inputs,
            self.evaluate,
            dtype.name,
            dtype.bits,
            machine,
            wide=False,
        )
        return [
            Case(number=0, dtype=dtype, payload=case, description=case.description)
            for case in cases
        ]

    def render(self, machine, instruction, case, out: CaseOutput) -> None:
        payload = case_payload(IntegerCase, case)
        instruction = as_elementwise(instruction)
        assert case.dtype is not None
        prefix = f"case{case.number}_{_stem(case.dtype)}_"
        out.text.extend(
            integer_case_lines(
                payload.labelled(prefix),
                instruction.form,
                instruction.name,
                case.dtype.name,
                case.dtype.bits,
                case.number,
                machine,
            )
        )
        out.data.extend(
            integer_case_data(
                payload.labelled(prefix),
                instruction.form,
                case.dtype.bits,
                machine,
            )
        )


class ElementwiseIntegerValueRules128(ElementwiseIntegerValueRules):
    """The same integer value rules, for datatypes that span M registers."""

    name = "elementwise_integer_value_rules_128"
    dtypes = domains.INTEGER128

    def build(self, machine, instruction, dtype) -> Sequence[Case]:
        instruction = as_elementwise(instruction)
        assert dtype is not None
        cases = integer_cases(
            instruction,
            self.inputs,
            self.evaluate,
            dtype.name,
            dtype.bits,
            machine,
            wide=True,
        )
        return [
            Case(number=0, dtype=dtype, payload=case, description=case.description)
            for case in cases
        ]


class ElementwiseSaturatingBoundary(ElementwiseTemplate):
    """Edge operands that force a saturating instruction to set amexsat."""

    name = "elementwise_saturating_boundary"
    dtypes = domains.FORMED_SATURATING_INTEGER

    def __init__(self, expectation: SaturatingExpectation, plan: CasePlan) -> None:
        """``expectation`` is which end clamps; ``plan`` carries the operands there.

        Both are stated by the instruction, as two arguments rather than one
        wrapper object, so the call site reads as the two facts it declares.
        """

        self.expectation = expectation
        self.plan = plan

    def fits_resources(self, machine, instruction, dtype=None) -> bool:
        return _integer_fits(machine, instruction, dtype)

    def build(self, machine, instruction, dtype) -> Sequence[Case]:
        instruction = as_elementwise(instruction)
        assert dtype is not None
        case = saturating_case(
            self.expectation,
            instruction.name,
            instruction.form,
            dtype.name,
            dtype.bits,
        )
        if case is None:
            return []
        return [Case(number=0, dtype=dtype, payload=case)]

    def render(self, machine, instruction, case, out: CaseOutput) -> None:
        instruction = as_elementwise(instruction)
        payload = case_payload(SaturatingCase, case)
        assert case.dtype is not None
        prefix = f"case_sat{case.number}_{_stem(case.dtype)}_"
        out.text.extend(
            saturating_case_lines(
                payload.labelled(prefix),
                self.plan,
                instruction.form,
                instruction.name,
                case.dtype.name,
                case.dtype.bits,
                case.number,
                machine,
            )
        )
        out.data.extend(
            saturating_case_data(
                payload.labelled(prefix), case.dtype.bits, machine
            )
        )


class ElementwiseSaturatingBoundary128(ElementwiseSaturatingBoundary):
    """The saturating boundary for 128-bit datatypes, which no scalar form has."""

    name = "elementwise_saturating_boundary_128"
    dtypes = domains.SATURATING_INTEGER128

    def fits_resources(self, machine, instruction, dtype=None) -> bool:
        if as_elementwise(instruction).form.takes_scalar:
            return False
        return super().fits_resources(machine, instruction, dtype)


class ElementwiseFloatNominal(ElementwiseTemplate):
    """One nominal softfloat case per datatype."""

    name = "elementwise_float_nominal"
    dtypes = domains.FORMED_SOFTFLOAT

    def __init__(self, evaluate: FloatFormula, comparison: bool = False) -> None:
        """``evaluate`` is the instruction's own formula for its answer.

        ``comparison`` says the answer is a comparison's mask, which the case
        builder cannot see in the formula: a comparison seeds its destination
        with the opposite result and needs three M groups.
        """

        self.evaluate = evaluate
        self.comparison = comparison

    def fits_resources(self, machine, instruction, dtype=None) -> bool:
        return _float_fits(machine, instruction, dtype, self.comparison)

    def build(self, machine, instruction, dtype) -> Sequence[Case]:
        assert dtype is not None
        case = float_case(
            partial(self.evaluate, instruction),
            self.comparison,
            dtype.name,
            dtype.bits,
        )
        return [Case(number=0, dtype=dtype, payload=case)]

    def render(self, machine, instruction, case, out: CaseOutput) -> None:
        instruction = as_elementwise(instruction)
        payload = case_payload(FloatCase, case)
        assert case.dtype is not None
        prefix = f"case{case.number}_{_stem(case.dtype)}_"
        out.text.extend(
            float_case_lines(
                payload.labelled(prefix),
                instruction.form,
                instruction.name,
                case.dtype.name,
                case.dtype.bits,
                case.number,
                machine,
            )
        )
        out.data.extend(
            float_case_data(payload.labelled(prefix), case.dtype.bits, machine)
        )


class ElementwiseFloatSpecialValues(ElementwiseTemplate):
    """NaN, infinity, and signed-zero behaviour, plus invalid operations."""

    name = "elementwise_float_special_values"
    dtypes = domains.FORMED_SOFTFLOAT

    def __init__(self, role: FloatArithmeticRole | FloatSpecialRole) -> None:
        """``role`` is the role this instruction's special values take.

        An arithmetic instruction hands its invalid-operation role; a comparison
        hands its special-value role.  Exactly one of the two, which is why the
        cases branch on the type instead of on a second declaration.
        """

        self.role = role

    def fits_resources(self, machine, instruction, dtype=None) -> bool:
        return _float_fits(
            machine, instruction, dtype, comparison_declared_by(instruction)
        )

    @property
    def _arithmetic_role(self) -> FloatArithmeticRole | None:
        """The role when this instruction's softfloat behaviour is arithmetic."""

        return self.role if isinstance(self.role, FloatArithmeticRole) else None

    @property
    def special(self) -> FloatSpecialRole:
        """The special-value role, or a loud failure for an arithmetic role."""

        if not isinstance(self.role, FloatSpecialRole):
            raise TypeError("this instruction's special values are arithmetic")
        return self.role

    def build(self, machine, instruction, dtype) -> Sequence[Case]:
        instruction = as_elementwise(instruction)
        assert dtype is not None
        role = self._arithmetic_role
        if role is not None:
            cases = float_arithmetic_cases(
                role,
                instruction.form,
                dtype.name,
                dtype.bits,
            )
        else:
            cases = float_special_cases(
                self.special,
                dtype.name,
                dtype.bits,
            )
        return [
            Case(
                number=0,
                dtype=dtype,
                payload=case,
                description=case.description,
            )
            for case in cases
        ]

    def render(self, machine, instruction, case, out: CaseOutput) -> None:
        instruction = as_elementwise(instruction)
        assert case.dtype is not None
        role = self._arithmetic_role
        if role is not None:
            payload = case_payload(FloatArithmeticCase, case)
            prefix = f"arith_special{case.number}_{_stem(case.dtype)}_"
            out.text.extend(
                float_arithmetic_case_lines(
                    payload.labelled(prefix),
                    instruction.form,
                    instruction.name,
                    case.dtype.name,
                    case.dtype.bits,
                    case.number,
                    machine,
                )
            )
            out.data.extend(
                float_arithmetic_case_data(
                    payload.labelled(prefix), case.dtype.bits, machine
                )
            )
            return
        payload = case_payload(FloatSpecialCase, case)
        prefix = f"special{case.number}_{_stem(case.dtype)}_"
        out.text.extend(
            float_special_case_lines(
                payload.labelled(prefix),
                self.special,
                instruction.form,
                instruction.name,
                case.dtype.name,
                case.dtype.bits,
                case.number,
                machine,
            )
        )
        out.data.extend(
            float_special_case_data(
                payload.labelled(prefix),
                instruction.form,
                case.dtype.bits,
                machine,
            )
        )


class ElementwiseFloatSemanticsSweep(ElementwiseTemplate):
    """The rounding-mode sweep: overflow, underflow, and halfway cases."""

    name = "elementwise_float_semantics_sweep"
    dtypes = domains.FORMED_SOFTFLOAT

    def __init__(self, role: FloatArithmeticRole) -> None:
        """``role`` is the invalid-operation vector the sweep carries."""

        self.role = role

    def fits_resources(self, machine, instruction, dtype=None) -> bool:
        return _float_fits(machine, instruction, dtype)

    def build(self, machine, instruction, dtype) -> Sequence[Case]:
        assert dtype is not None
        operands = rounding_operands(dtype.name, dtype.bits)
        return [Case(number=0, dtype=dtype, payload=operands)]

    def render(self, machine, instruction, case, out: CaseOutput) -> None:
        instruction = as_elementwise(instruction)
        assert case.dtype is not None
        case_payload(RoundingOperands, case)
        text, data = rounding_case_lines(
            self.role,
            instruction.form,
            instruction.name,
            case.dtype.name,
            case.dtype.bits,
            case.number,
            machine,
        )
        out.text.extend(text)
        out.data.extend(data)


def _stem(dtype: DType) -> str:
    return dtype_stem(dtype.name)


#: The elementwise template classes, in the order their cases appear in a source.
#: Each instruction instantiates the ones it runs and passes each its input, so
#: this tuple is the canonical order the tests check those lists against.
ELEMENTWISE_TEMPLATE_CLASSES = (
    ElementwiseIntegerValueRules,
    ElementwiseIntegerValueRules128,
    ElementwiseSaturatingBoundary,
    ElementwiseSaturatingBoundary128,
    ElementwiseFloatNominal,
    ElementwiseFloatSpecialValues,
    ElementwiseFloatSemanticsSweep,
)

__all__ = [
    "ELEMENTWISE_TEMPLATE_CLASSES",
    "ElementwiseFloatSemanticsSweep",
    "ElementwiseFloatSpecialValues",
    "ElementwiseIntegerValueRules",
    "ElementwiseIntegerValueRules128",
    "ElementwiseSaturatingBoundary",
    "ElementwiseSaturatingBoundary128",
    "ElementwiseTemplate",
]
