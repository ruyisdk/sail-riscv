"""Shared declaration of the forty-six elementwise instructions.

Every elementwise instruction states its operand form, what it computes on one
element (``evaluate``), and -- when it has a nominal softfloat case -- the answer
it expects there (``evaluate_float``).  Then it lists the templates it runs, each
constructed with what it checks::

    class MaddEw(ElementwiseInstruction):
        form = ElementwiseForm.BINARY_M

        def evaluate(self, elements: IntegerElements) -> int:
            # ``D = A + B`` element by element.
            return elements.lhs + elements.rhs

        def evaluate_float(self, dtype_name: str, element_bits: int) -> int:
            # The softfloat model's nominal ``add`` operand is the answer.
            return FLOAT_OPERATION_VALUES[dtype_name]["add"]

        templates = (
            ElementwiseIntegerValueRules(BASE_INTEGER_INPUT_CASES, evaluate),
            ElementwiseIntegerValueRules128(BASE_INTEGER_INPUT_CASES, evaluate),
            ElementwiseSaturatingBoundary(SaturatingExpectation.MAX, CasePlan(...)),
            ElementwiseFloatNominal(evaluate_float),
            ...
        )

Both formulas are defined before the list and handed to the templates that use
them, so the class body shows what the checks compare against.  They are the
members that are passed on rather than named, because they are functions -- and
the base keeps no default for either, so an instruction that forgot to hand one
over fails at class-definition time with a missing argument.  The softfloat
sweep and special-value templates take no formula: each of their cases is a whole
vector of questions (six rounding modes, every NaN and infinity encoding), not
one operation with one answer.

An ``evaluate_float`` whose answer is a comparison's mask is declared as
``ElementwiseFloatNominal(evaluate_float, comparison=True)``, because only the
template can see the two things that go with it: the opposite answer is seeded into
the destination, and the case needs three independent M register groups.

A template is constructed with its input, so the instance carries what it checks and
the list *is* this instruction's list of checks, in the order its cases appear in
a source.  Nothing filters that list afterwards: what is written is what runs.
The repetition is deliberate -- each class body reads on its own, and the tests
check the lists against the family's canonical order.

The seven template classes a list may use are in
:data:`mmul_gen.templates.elementwise_templates.ELEMENTWISE_TEMPLATE_CLASSES`, and
this module re-exports them.  ``form`` stays outside the list: every template
branches on the operand form, so it is what the instruction *is* rather than
something handed to one template.
"""

from __future__ import annotations

from mmul_gen.asm import dst_square_lines
from mmul_gen.inputs import (
    BASE_INTEGER_INPUT_CASES,
    IntegerInputCase,
    IntegerInputKind,
    IntegerOverflowCase,
    overflow,
)
from fp_semantics import FLOAT_OPERATION_VALUES

from mmul_gen.instruction import Instruction
from mmul_gen.machine import MachineConfig
from mmul_gen.templates.elementwise_elements import (
    IntegerElements,
    round_to_nearest_up,
)
from mmul_gen.templates.elementwise_float import FloatFormula
from mmul_gen.templates.elementwise_float_arithmetic import FloatArithmeticRole
from mmul_gen.templates.elementwise_float_special import (
    FloatSpecialRole,
)
from mmul_gen.templates.elementwise_forms import ElementwiseForm
from mmul_gen.templates.elementwise_saturating import (
    SaturatingExpectation,
)
from mmul_gen.templates.base import Template
from mmul_gen.templates.elementwise_templates import (
    ElementwiseFloatNominal,
    ElementwiseFloatSemanticsSweep,
    ElementwiseFloatSpecialValues,
    ElementwiseIntegerValueRules,
    ElementwiseIntegerValueRules128,
    ElementwiseSaturatingBoundary,
    ElementwiseSaturatingBoundary128,
)


class ElementwiseInstruction(Instruction, family_base=True):
    """One elementwise operation, in one operand form."""

    form: ElementwiseForm

    #: Every template this instruction runs, in the order its cases appear in a
    #: source.  Each entry is that template constructed with its own input, so
    #: the list states the instruction's whole check set and no template runs that
    #: is not written here.  Declaring it is not optional -- the base states no
    #: default, so an instruction without a list fails at class-definition time.
    templates: tuple[Template, ...]

    def data_footer(self, machine: MachineConfig) -> list[str]:
        """Every elementwise source ends with the shared scratch square."""

        return dst_square_lines(machine)

    @property
    def input_case_names(self) -> tuple[str, ...]:
        """The names of the integer input cases this instruction runs.

        Read from the integer template it constructed, so the inventory is stated
        once -- in :attr:`templates` -- and no second declaration can drift from
        what the templates actually sweep.
        """

        for template in self.templates:
            if isinstance(template, ElementwiseIntegerValueRules):
                return tuple(case.name for case in template.inputs)
        raise TypeError(f"{self.name} runs no integer template")


__all__ = [
    "BASE_INTEGER_INPUT_CASES",
    "ElementwiseFloatNominal",
    "ElementwiseFloatSemanticsSweep",
    "ElementwiseFloatSpecialValues",
    "ElementwiseForm",
    "ElementwiseIntegerValueRules",
    "ElementwiseIntegerValueRules128",
    "ElementwiseSaturatingBoundary",
    "ElementwiseSaturatingBoundary128",
    "ElementwiseInstruction",
    "FLOAT_OPERATION_VALUES",
    "FloatArithmeticRole",
    "FloatFormula",
    "FloatSpecialRole",
    "IntegerElements",
    "IntegerInputCase",
    "IntegerInputKind",
    "IntegerOverflowCase",
    "SaturatingExpectation",
    "overflow",
    "round_to_nearest_up",
]
